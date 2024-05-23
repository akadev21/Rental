from odoo import models, fields, api


class LastEnteredValues(models.Model):
    _name = 'last.entered.values'
    _description = 'Last Entered Values'

    wizard = fields.Selection([
        ('pickup', 'Pickup'),
        ('return', 'Return')
    ], string='Wizard')
    line_ids = fields.One2many('last.entered.values.line', 'wizard_id', string='Order Lines')


class LastEnteredValuesLine(models.Model):
    _name = 'last.entered.values.line'
    _description = 'Last Entered Values Line'

    wizard_id = fields.Many2one('last.entered.values', string='Wizard Reference')
    product_id = fields.Many2one('product.product', string='Product')
    quantity_reserved = fields.Float(string='Quantity Reserved')
    quantity_to_pickup = fields.Float(string='Quantity Delivered')
