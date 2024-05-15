from odoo import models, fields, api


class RentalPricing(models.Model):
    _name = 'rental.pricing'
    _description = 'Rental Pricing'

    product_template_id = fields.Many2one('product.template', string='Product Template', required=True)
    period_id = fields.Many2one('rental.period', string='Rental Period', required=True)
    duration = fields.Float(related='period_id.duration', string='Duration', readonly=True)
    price = fields.Float(string='Price',  store=True)  # Make it computed and stored
    price_list_id = fields.Many2one('product.pricelist', string='Price List')

    _sql_constraints = [
        ('unique_pricing',
         'UNIQUE(product_template_id, period_id)',
         'A unique price must exist for each product template and period.')
    ]

