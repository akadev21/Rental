from odoo import models, fields, api, exceptions

class RentalStock(models.Model):
    _name = 'rental.stock'
    _description = 'Rental Stock'

    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    reserved_qty = fields.Float(string='Reserved Quantity', required=True, default=0)
    rented_qty = fields.Float(string='Rented Quantity', required=True, default=0)
    returned_qty = fields.Float(string='Returned Quantity', required=True, default=0)
    return_date = fields.Datetime(string='Return Date', help="Date when the product was returned")
    rental_return_date = fields.Datetime(string='Expected Return Date')

    state = fields.Selection([
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('available', 'Available'),
    ], string='Status', default='reserved', required=True)

    @api.constrains('reserved_qty', 'rented_qty', 'returned_qty')
    def _check_quantities(self):
        for record in self:
            if record.reserved_qty < 0 or record.rented_qty < 0 or record.returned_qty < 0:
                raise exceptions.ValidationError("Quantities cannot be negative.")

    @api.model
    def get_reservation_info(self):
        reservation_info = {}
        for stock in self:
            if stock.reserved_qty > 0:
                reservations = self.env['rental.reservation'].search([
                    ('product_id', '=', stock.product_id.id),
                    ('start_date', '<=', fields.Datetime.now()),
                    ('end_date', '>=', fields.Datetime.now()),
                ])
                if reservations:
                    reservation = reservations[0]
                    reservation_info[stock.id] = {
                        'client': reservation.order_id.partner_id.name,
                        'start_date': reservation.start_date,
                        'end_date': reservation.end_date,
                    }
        return reservation_info

    def update_stock(self, reserved_qty_change=0, rented_qty_change=0, returned_qty_change=0, return_date=None):
        self.ensure_one()
        new_reserved_qty = self.reserved_qty + reserved_qty_change
        new_rented_qty = self.rented_qty + rented_qty_change
        new_returned_qty = self.returned_qty + returned_qty_change

        if new_reserved_qty < 0 or new_rented_qty < 0 or new_returned_qty < 0:
            raise exceptions.ValidationError("Quantities cannot be negative.")

        update_vals = {
            'reserved_qty': new_reserved_qty,
            'rented_qty': new_rented_qty,
            'returned_qty': new_returned_qty,
        }

        if return_date:
            update_vals['return_date'] = return_date

        self.write(update_vals)

        # Update state based on quantities
        if new_reserved_qty == 0 and new_rented_qty > 0:
            self.state = 'rented'
        elif new_rented_qty == 0 and new_returned_qty > 0:
            self.state = 'available'

        # Update order state if all rented items are returned
        if self.order_id:
            order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
            all_rented_zero = all(line.rented_qty == 0 for line in order_lines)
            if all_rented_zero:
                self.order_id.write({'state': 'done'})

    def return_items(self, quantity_to_return=0, return_date=None):
        self.ensure_one()
        if quantity_to_return <= 0:
            return  # Return immediately if no valid quantity to return

        if quantity_to_return > self.rented_qty:
            raise exceptions.ValidationError('Quantity to Return cannot exceed Rented Quantity.')

        # Update rented_qty and returned_qty
        self.update_stock(rented_qty_change=-quantity_to_return, returned_qty_change=quantity_to_return, return_date=return_date)
