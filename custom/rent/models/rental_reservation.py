from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class RentalReservation(models.Model):
    _name = 'rental.reservation'
    _description = 'Rental Reservation'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    order_id = fields.Many2one('sale.order', string='Rental Order', required=True)
    start_date = fields.Datetime(string='Start Date', required=True, default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime(string='End Date', required=True, default=lambda self: fields.Datetime.now())
    quantity_reserved = fields.Float(string='Quantity Reserved')
    quantity_to_pickup = fields.Float(string='Quantity Delivered')
    order_state = fields.Selection(related='order_id.state', string='Order State', readonly=True)

    _sql_constraints = [
        ('reservation_unique', 'unique(product_id, start_date, end_date, order_id)',
         'The product is already reserved for this period in this order.')
    ]

    @api.depends('order_id.state')
    def _compute_order_state(self):
        """ Compute method to trigger actions based on order state """
        for reservation in self:
            if reservation.order_state == 'done':
                reservation.delete_reservations_for_done_order()

    @api.model
    def create(self, values):
        product_id = values.get('product_id')
        start_date = fields.Datetime.to_datetime(values.get('start_date'))
        end_date = fields.Datetime.to_datetime(values.get('end_date'))
        quantity_reserved = values.get('quantity_reserved', 0.0)

        _logger.info(f"Starting reservation creation - Product ID: {product_id}, "
                     f"Start Date: {start_date}, End Date: {end_date}, Quantity Reserved: {quantity_reserved}")

        if product_id and start_date and end_date:
            product = self.env['product.product'].browse(product_id)

            _logger.info(f"Fetched product details - Product Name: {product.name}, "
                         f"On Reserve Quantity: {product.on_reserve}, On Rent Quantity: {product.on_rent}")

            # Calculate available quantity for rental
            available_quantity = product.qty_available - product.on_reserve - product.on_rent

            _logger.info(f"Calculated available quantity - Available Quantity: {available_quantity}")

            # Calculate total reserved quantity within the specified period
            existing_reservations = self.search([
                ('product_id', '=', product_id),
                ('start_date', '<', end_date),
                ('end_date', '>', start_date),
                ('id', '!=', values.get('id'))  # Exclude current reservation if editing
            ])
            total_reserved_quantity = sum(existing_reservations.mapped('quantity_reserved'))

            _logger.info(f"Calculated total reserved quantity - Total Reserved Quantity: {total_reserved_quantity}")

            # Check if requested quantity exceeds available quantity
            if quantity_reserved > (available_quantity - total_reserved_quantity):
                raise exceptions.ValidationError('Not enough quantity available for reservation.')

            _logger.info("Validation passed - Creating reservation")

            # Create the reservation if everything is valid
            reservation = super(RentalReservation, self).create(values)

            _logger.info("Reservation created successfully")

            return reservation
        else:
            return super(RentalReservation, self).create(values)

    def write(self, values):
        res = super(RentalReservation, self).write(values)
        return res

    def unlink(self):
        res = super(RentalReservation, self).unlink()
        return res

    @api.onchange('order_id', 'product_id')
    def _onchange_order_product(self):
        if self.order_id and self.product_id:
            order_line = self.env['sale.order.line'].search([
                ('order_id', '=', self.order_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if order_line:
                self.quantity_reserved = order_line.product_uom_qty

    @api.constrains('quantity_reserved', 'quantity_to_pickup')
    def _check_quantity(self):
        for reservation in self:
            if reservation.quantity_reserved < 0:
                raise exceptions.ValidationError('Reserved quantity cannot be negative.')
            if reservation.quantity_to_pickup < 0:
                raise exceptions.ValidationError('Delivered quantity cannot be negative.')

    def delete_reservations_for_done_order(self):
        """ Delete reservations associated with products in a 'done' rental order """
        products_in_order = self.env['rental.reservation'].search([
            ('order_id', '=', self.order_id.id),
            ('order_id.state', '=', 'done')
        ])
        products_in_order.unlink()
