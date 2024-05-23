from odoo import models, fields, api, exceptions


class RentalStock(models.Model):
    _name = 'rental.stock'
    _description = 'Rental Stock'

    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    reserved_qty = fields.Float(string='Reserved Quantity', required=True, default=0)
    rented_qty = fields.Float(string='Rented Quantity', required=True, default=0)
    returned_qty = fields.Float(string='Returned Quantity', required=True, default=0)
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

    def update_stock(self, reserved_qty_change=0, rented_qty_change=0, returned_qty_change=0):
        self.ensure_one()
        new_reserved_qty = self.reserved_qty + reserved_qty_change
        new_rented_qty = self.rented_qty + rented_qty_change
        new_returned_qty = self.returned_qty + returned_qty_change

        if new_reserved_qty < 0 or new_rented_qty < 0 or new_returned_qty < 0:
            raise exceptions.ValidationError("Quantities cannot be negative.")

        self.write({
            'reserved_qty': new_reserved_qty,
            'rented_qty': new_rented_qty,
            'returned_qty': new_returned_qty,
        })

        if new_reserved_qty == 0 and new_rented_qty > 0:
            self.state = 'rented'
        elif new_rented_qty == 0 and new_returned_qty > 0:
            self.state = 'available'
