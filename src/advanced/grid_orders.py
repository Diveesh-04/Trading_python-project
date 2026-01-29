import time
from decimal import Decimal
from ..client import BinanceFuturesClient
from ..validators import OrderValidator
from ..logger import logger

class GridOrder:
    """
    Handle Grid Orders
    Automated buy-low/sell-high within a price range
    """
    
    def __init__(self, client: BinanceFuturesClient = None):
        self.client = client or BinanceFuturesClient()
        self.validator = OrderValidator()
    
    def execute(self, symbol: str, lower_price: str, upper_price: str,
                grid_levels: int, quantity_per_level: str):
        """
        Execute a grid order
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            lower_price: Lower bound of price range
            upper_price: Upper bound of price range
            grid_levels: Number of grid levels
            quantity_per_level: Quantity to trade at each level
        """
        
        # Validate inputs
        is_valid, error_msg = self.validator.validate_symbol(symbol)
        if not is_valid:
            return {"success": False, "error": error_msg}
        
        lower, error_msg = self.validator.validate_price(lower_price)
        if lower is None:
            return {"success": False, "error": error_msg}
        
        upper, error_msg = self.validator.validate_price(upper_price)
        if upper is None:
            return {"success": False, "error": error_msg}
        
        if lower >= upper:
            return {"success": False, "error": "Lower price must be less than upper price"}
        
        if grid_levels < 2:
            return {"success": False, "error": "Grid levels must be at least 2"}
        
        qty, error_msg = self.validator.validate_quantity(quantity_per_level)
        if qty is None:
            return {"success": False, "error": error_msg}
        
        try:
            # Get current price and precision
            current_price = Decimal(str(self.client.get_price(symbol)))
            price_precision = self.client.get_price_precision(symbol)
            qty_precision = self.client.get_quantity_precision(symbol)
            
            # Validate current price is within range
            if current_price < lower or current_price > upper:
                logger.warning(
                    f"Current price (${current_price}) is outside grid range "
                    f"(${lower} - ${upper}). Grid will still be placed."
                )
            
            # Calculate grid prices
            price_step = (upper - lower) / (grid_levels - 1)
            grid_prices = [lower + (price_step * i) for i in range(grid_levels)]
            
            # Round prices
            grid_prices = [round(float(p), price_precision) for p in grid_prices]
            
            # Round quantity
            qty_rounded = round(float(qty), qty_precision)
            
            # Ensure minimum notional per level
            min_notional = float(self.validator.MIN_NOTIONAL)
            min_qty = min_notional / min(grid_prices)
            if qty_rounded < min_qty:
                qty_rounded = round(min_qty, qty_precision)
                logger.info(f"Adjusted quantity to {qty_rounded} to meet minimum notional per level")
            
            logger.info(
                f"Placing GRID order for {symbol}: {grid_levels} levels, "
                f"{qty_rounded} per level, range: ${lower} - ${upper} "
                f"(current: ${current_price})"
            )
            
            orders = []
            
            # Place buy orders below current price, sell orders above
            for i, price in enumerate(grid_prices):
                if price < current_price:
                    # Place buy limit order
                    side = 'BUY'
                    order_type = 'LIMIT'
                elif price > current_price:
                    # Place sell limit order
                    side = 'SELL'
                    order_type = 'LIMIT'
                else:
                    # Skip current price level
                    logger.info(f"Skipping grid level at current price: ${price}")
                    continue
                
                try:
                    order = self.client.client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type=order_type,
                        timeInForce='GTC',
                        quantity=qty_rounded,
                        price=price
                    )
                    
                    orders.append({
                        "order_id": order['orderId'],
                        "side": side,
                        "price": price,
                        "quantity": qty_rounded,
                        "status": order['status'],
                        "level": i + 1
                    })
                    
                    logger.info(f"Grid level {i+1}/{grid_levels}: {side} order @ ${price} - Order {order['orderId']}")
                    
                    # Small delay to avoid rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to place grid order at level {i+1} (${price}): {e}")
                    continue
            
            total_buy = sum(1 for o in orders if o['side'] == 'BUY')
            total_sell = sum(1 for o in orders if o['side'] == 'SELL')
            
            logger.info(
                f"Grid order placed: {len(orders)} orders total "
                f"({total_buy} buy, {total_sell} sell)"
            )
            
            return {
                "success": True,
                "symbol": symbol,
                "grid_levels": grid_levels,
                "price_range": {"lower": float(lower), "upper": float(upper)},
                "quantity_per_level": qty_rounded,
                "current_price": float(current_price),
                "orders_placed": len(orders),
                "buy_orders": total_buy,
                "sell_orders": total_sell,
                "orders": orders
            }
            
        except Exception as e:
            logger.error(f"Grid order failed: {e}")
            return {"success": False, "error": str(e)}
