from odoo import models, fields, api, exceptions


class RentalReservation(models.Model):
    _name = 'rental.reservation'
    _description = 'Rental Reservation'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    order_id = fields.Many2one('sale.order', string='Rental Order', required=True)
    start_date = fields.Datetime(string='Start Date', required=True, default=lambda self: fields.Datetime.now())
    end_date = fields.Datetime(string='End Date', required=True, default=lambda self: fields.Datetime.now())
    quantity_reserved = fields.Float(string='Quantity Reserved')
    quantity_to_pickup = fields.Float(string='Quantity Delivered')

    _sql_constraints = [
        ('reservation_unique', 'unique(product_id, start_date, end_date)',
         'The product is already reserved for this period.')
    ]

    @api.model
    def create(self, values):
        if 'start_date' not in values:
            values['start_date'] = fields.Datetime.now()
        if 'end_date' not in values:
            values['end_date'] = fields.Datetime.now()
        reservation = super(RentalReservation, self).create(values)
        reservation.product_id.product_tmpl_id._compute_on_rent()
        return reservation

    def write(self, values):
        if 'start_date' in values and not values.get('start_date'):
            values['start_date'] = fields.Datetime.now()
        if 'end_date' in values and not values.get('end_date'):
            values['end_date'] = fields.Datetime.now()
        res = super(RentalReservation, self).write(values)
        for record in self:
            record.product_id.product_tmpl_id._compute_on_rent()
        return res

    def unlink(self):
        products = self.mapped('product_id.product_tmpl_id')
        res = super(RentalReservation, self).unlink()
        for product in products:
            product._compute_on_rent()
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
