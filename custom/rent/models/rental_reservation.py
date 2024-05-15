from odoo import models, fields


class RentalReservation(models.Model):
    _name = 'rental.reservation'

    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Integer(string='Quantity')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    order_id = fields.Many2one('sale.order', string='Order')
