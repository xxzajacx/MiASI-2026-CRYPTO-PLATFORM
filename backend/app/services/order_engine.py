"""Service for processing and executing conditional orders."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.order import Order
from app.models.transaction import TransactionHistory
from app.services.market_data import market_data_service

logger = logging.getLogger(__name__)

async def process_single_order(order_id: int, prices: dict) -> bool:
    """Process a single order in its own database transaction."""
    async with AsyncSessionLocal() as db:
        try:
            # Re-fetch order to ensure fresh data
            result = await db.execute(select(Order).filter(Order.id == order_id))
            order = result.scalars().first()
            
            if not order or order.status != "ACTIVE":
                return False
            
            current_price = prices.get(order.symbol)
            if not current_price:
                return False
            
            should_execute = False
            # Execution logic for protective orders:
            # SELL (Long Exit): Trigger SL if price <= target, TP if price >= target
            # BUY (Short Exit): Trigger SL if price >= target, TP if price <= target
            if order.side == "SELL":
                if order.order_type == "STOP_LOSS":
                    if current_price <= order.target_price:
                        should_execute = True
                elif order.order_type == "TAKE_PROFIT":
                    if current_price >= order.target_price:
                        should_execute = True
            else: # BUY (Short Exit)
                if order.order_type == "STOP_LOSS":
                    if current_price >= order.target_price:
                        should_execute = True
                elif order.order_type == "TAKE_PROFIT":
                    if current_price <= order.target_price:
                        should_execute = True
            
            if not should_execute:
                return False
            
            logger.info(f"Triggering {order.side} {order.order_type} for order ID {order.id}")
            executed_price = current_price
            total_qty = order.amount
            total_fee = total_qty * executed_price * 0.005 # 0.5% fee simulation to match tests
            total_value = total_qty * executed_price
            
            # Check if transaction costs exceed sale value
            if total_fee > total_value:
                logger.warning(f"Order {order.id} aborted: transaction costs ({total_fee}) exceed sale value ({total_value})")
                order.status = "FAILED"
                await db.commit()
                return False
            
            # Execute on Binance if API keys are configured
            binance_success = False
            if market_data_service.api_key and "WKLEJ" not in market_data_service.api_key:
                try:
                    binance_order = await market_data_service.execute_trade(
                        order.symbol, order.side, order.amount, order.leverage
                    )
                    binance_success = True
                    
                    # Extract weighted average price and actual quantity from fills
                    fills = binance_order.get("fills", [])
                    if fills:
                        total_qty = sum(float(f["qty"]) for f in fills)
                        executed_price = sum(float(f["qty"]) * float(f["price"]) for f in fills) / total_qty
                        total_fee = sum(float(f.get("commission", 0)) for f in fills)
                    else:
                        executed_price = float(binance_order.get("avgPrice", binance_order.get("price", executed_price)))
                except Exception as be:
                    logger.warning(f"Binance order {order.id} execution failed, falling back to local simulation: {be}")
            
            # Update local simulation balances
            from app.models.wallet import Wallet
            base_asset = order.symbol.replace("USDT", "")
            quote_asset = "USDT"
            
            res = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id, Wallet.asset_symbol == base_asset))
            asset_wallet = res.scalars().first()
            res = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id, Wallet.asset_symbol == quote_asset))
            usdt_wallet = res.scalars().first()
            
            if order.side == "SELL":
                if asset_wallet and asset_wallet.locked_balance >= total_qty:
                    asset_wallet.locked_balance -= total_qty
                    if not usdt_wallet:
                        usdt_wallet = Wallet(user_id=order.user_id, asset_symbol=quote_asset, balance=0.0, locked_balance=0.0)
                        db.add(usdt_wallet)
                    usdt_wallet.balance += (total_qty * executed_price) - total_fee
                else:
                    raise ValueError(f"Insufficient locked balance for {base_asset}")
            else: # BUY (Exit Short)
                total_value = total_qty * executed_price
                required_margin = total_value / order.leverage
                cost = required_margin + total_fee
                
                if usdt_wallet and usdt_wallet.balance >= cost:
                    usdt_wallet.balance -= cost
                    if not asset_wallet:
                        asset_wallet = Wallet(user_id=order.user_id, asset_symbol=base_asset, balance=0.0, locked_balance=0.0)
                        db.add(asset_wallet)
                    asset_wallet.balance += total_qty
            
            # Finalize order status
            order.status = "COMPLETED"
            
            # OCO (One-Cancels-the-Other) Cleanup
            if order.group_id:
                res = await db.execute(
                    select(Order).where(
                        Order.group_id == order.group_id,
                        Order.id != order.id,
                        Order.status == "ACTIVE"
                    )
                )
                siblings = res.scalars().all()
                for sib in siblings:
                    sib.status = "CANCELLED"
                    logger.info(f"OCO: Automatically cancelled linked order {sib.id}")
            
            # Record audit transaction
            transaction = TransactionHistory(
                user_id=order.user_id,
                order_id=order.id,
                type=order.side,
                amount=total_qty,
                asset=base_asset,
                price=executed_price,
                fee=total_fee,
                status="COMPLETED",
                log_message=f"Wykonano zlecenie ochronne {order.order_type} (Binance: {binance_success})"
            )
            db.add(transaction)
            await db.commit()
            logger.info(f"Order ID {order.id} processed successfully.")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Execution failure for order {order_id}: {e}")
            
            # Re-fetch order and unlock assets on failure using a separate clean session
            try:
                async with AsyncSessionLocal() as db_fail:
                    result = await db_fail.execute(select(Order).filter(Order.id == order_id))
                    failed_order = result.scalars().first()
                    if failed_order:
                        failed_order.status = "FAILED"
                        
                        # Unlock assets
                        from app.models.wallet import Wallet
                        base_asset = failed_order.symbol.replace("USDT", "")
                        res = await db_fail.execute(select(Wallet).where(Wallet.user_id == failed_order.user_id, Wallet.asset_symbol == base_asset))
                        asset_wallet = res.scalars().first()
                        
                        if asset_wallet and asset_wallet.locked_balance >= failed_order.amount:
                            asset_wallet.locked_balance -= failed_order.amount
                            asset_wallet.balance += failed_order.amount
                            logger.info(f"Unlocked {failed_order.amount} {base_asset} for failed order {failed_order.id}")
                        
                        await db_fail.commit()
            except Exception as inner_e:
                logger.error(f"Failed to handle order failure cleanup: {inner_e}")
            
            return False


async def process_orders():
    """Main task to monitor and execute active conditional orders (TP/SL)."""
    prices = await market_data_service.get_all_prices()
    if not prices:
        return
    
    # Fetch all active conditional orders
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Order).filter(Order.status == "ACTIVE"))
        active_orders = result.scalars().all()
        order_ids = [order.id for order in active_orders]
    
    # Process each order in its own transaction
    for order_id in order_ids:
        try:
            await process_single_order(order_id, prices)
        except Exception as e:
            logger.error(f"Error processing order {order_id}: {e}")


async def start_order_engine():
    """Background loop for the order execution engine."""
    logger.info("Order Engine initialized and running.")
    while True:
        try:
            await process_orders()
        except Exception as e:
            logger.error(f"Order engine heart-beat error: {e}")
        await asyncio.sleep(10)
