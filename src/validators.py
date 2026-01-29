import re
from decimal import Decimal, InvalidOperation
from .logger import logger

class OrderValidator:
    """Validate trading inputs with comprehensive checks"""
    
    MIN_NOTIONAL = Decimal('100')  # Binance minimum order value
    MAX_PRICE_THRESHOLD = Decimal('1000000000')  # Maximum reasonable price
    MAX_QUANTITY_THRESHOLD = Decimal('1000000')  # Maximum reasonable quantity
    
    # Common trading pairs pattern
    SYMBOL_PATTERN = re.compile(r'^[A-Z]{2,10}(USDT|BUSD|BTC|ETH)$')
    
    @staticmethod
    def validate_symbol(symbol: str) -> tuple[bool, str]:
        """
        Validate symbol format and structure
        Returns: (is_valid, error_message)
        """
        if not symbol:
            return False, "Symbol cannot be empty"
        
        symbol_upper = symbol.upper()
        
        # Length check
        if len(symbol_upper) < 6 or len(symbol_upper) > 20:
            return False, f"Symbol length invalid: {symbol} (must be 6-20 characters)"
        
        # Format check (basic pattern)
        if not OrderValidator.SYMBOL_PATTERN.match(symbol_upper):
            logger.warning(f"Symbol format may be unusual: {symbol_upper}")
            # Don't fail, just warn - some symbols might not match pattern
        
        # Check for common issues
        if ' ' in symbol:
            return False, f"Symbol contains spaces: {symbol}"
        
        return True, ""
    
    @staticmethod
    def validate_quantity(quantity: str) -> tuple[Decimal | None, str]:
        """
        Validate and convert quantity to Decimal with comprehensive checks
        Returns: (quantity_decimal, error_message)
        """
        if not quantity or not quantity.strip():
            return None, "Quantity cannot be empty"
        
        try:
            qty = Decimal(str(quantity).strip())
            
            if qty <= 0:
                return None, f"Quantity must be positive: {quantity}"
            
            if qty > OrderValidator.MAX_QUANTITY_THRESHOLD:
                return None, f"Quantity too large: {quantity} (max: {OrderValidator.MAX_QUANTITY_THRESHOLD})"
            
            # Check for reasonable minimum (very small quantities might be errors)
            if qty < Decimal('0.00000001'):
                logger.warning(f"Very small quantity: {quantity}")
            
            return qty, ""
            
        except (InvalidOperation, ValueError) as e:
            return None, f"Invalid quantity format: {quantity} ({str(e)})"
    
    @staticmethod
    def validate_price(price: str, min_price: Decimal = None, max_price: Decimal = None) -> tuple[Decimal | None, str]:
        """
        Validate price input with threshold checks
        Returns: (price_decimal, error_message)
        """
        if not price or not price.strip():
            return None, "Price cannot be empty"
        
        try:
            price_dec = Decimal(str(price).strip())
            
            if price_dec <= 0:
                return None, f"Price must be positive: {price}"
            
            if price_dec > OrderValidator.MAX_PRICE_THRESHOLD:
                return None, f"Price too large: {price} (max: ${OrderValidator.MAX_PRICE_THRESHOLD})"
            
            # Check against min/max if provided
            if min_price is not None and price_dec < min_price:
                return None, f"Price below minimum: ${price_dec} < ${min_price}"
            
            if max_price is not None and price_dec > max_price:
                return None, f"Price above maximum: ${price_dec} > ${max_price}"
            
            return price_dec, ""
            
        except (InvalidOperation, ValueError) as e:
            return None, f"Invalid price format: {price} ({str(e)})"
    
    @staticmethod
    def validate_side(side: str) -> tuple[bool, str]:
        """
        Validate order side (BUY/SELL)
        Returns: (is_valid, error_message)
        """
        if not side:
            return False, "Order side cannot be empty"
        
        side_upper = side.upper().strip()
        if side_upper not in ['BUY', 'SELL']:
            return False, f"Invalid side: {side}. Must be BUY or SELL"
        
        return True, ""
    
    @staticmethod
    def validate_notional(quantity: Decimal, price: Decimal) -> tuple[bool, str]:
        """
        Validate that order notional value meets Binance minimum ($100)
        Returns: (is_valid, error_message)
        """
        notional = quantity * price
        if notional < OrderValidator.MIN_NOTIONAL:
            min_qty = OrderValidator.MIN_NOTIONAL / price
            return False, (
                f"Order value (${notional:.2f}) is below Binance minimum of ${OrderValidator.MIN_NOTIONAL}. "
                f"Minimum quantity for this price: {min_qty:.6f}"
            )
        return True, ""
    
    @staticmethod
    def validate_limit_price(price: Decimal, current_price: Decimal, side: str) -> tuple[bool, str]:
        """
        Validate limit price is reasonable compared to current price
        Returns: (is_valid, error_message)
        """
        side_upper = side.upper()
        
        if side_upper == 'BUY':
            # For buy orders, limit price should be below current price (or slightly above for market orders)
            if price > current_price * Decimal('1.1'):  # More than 10% above
                return False, (
                    f"Limit buy price (${price}) is more than 10% above current price (${current_price}). "
                    f"This seems unusual. Current price: ${current_price}"
                )
        elif side_upper == 'SELL':
            # For sell orders, limit price should be above current price (or slightly below)
            if price < current_price * Decimal('0.9'):  # More than 10% below
                return False, (
                    f"Limit sell price (${price}) is more than 10% below current price (${current_price}). "
                    f"This seems unusual. Current price: ${current_price}"
                )
        
        return True, ""