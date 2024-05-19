from odoo import models, fields, api, exceptions


class RentalReservation(models.Model):
    _name = 'rental.reservation'
    _description = 'Rental Reservation'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    order_id = fields.Many2one('sale.order', string='Rental Order', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    quantity_reserved = fields.Float(string='Quantity Reserved')  # Renamed field
    quantity_delivered = fields.Float(string='Quantity Delivered')

    _sql_constraints = [
        ('reservation_unique', 'unique(product_id, start_date, end_date)',
         'The product is already reserved for this period.')
    ]

    @api.model
    def create(self, values):
        if 'quantity_reserved' not in values:
            order_line = self.env['sale.order.line'].search([
                ('order_id', '=', values.get('order_id')),
                ('product_id', '=', values.get('product_id'))
            ], limit=1)
            if order_line:
                values['quantity_reserved'] = order_line.product_uom_qty
        return super(RentalReservation, self).create(values)

    @api.onchange('order_id', 'product_id')
    def _onchange_order_product(self):
        if self.order_id and self.product_id:
            order_line = self.env['sale.order.line'].search([
                ('order_id', '=', self.order_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if order_line:
                self.quantity_reserved = order_line.product_uom_qty

    @api.constrains('product_id', 'start_date', 'end_date')
    def _check_reservation_dates(self):
        for reservation in self:
            overlapping_reservations = self.env['rental.reservation'].search([
                ('product_id', '=', reservation.product_id.id),
                ('id', '!=', reservation.id),
                ('start_date', '<', reservation.end_date),
                ('end_date', '>', reservation.start_date),
            ])
            if overlapping_reservations:
                raise exceptions.ValidationError('The product is already reserved for the selected period.')
