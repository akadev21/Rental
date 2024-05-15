from odoo import models, fields


class RentalPeriod(models.Model):
    _name = 'rental.period'
    _description = 'Rental Period'

    name = fields.Char(string='Name', required=True)
    duration = fields.Float(string='Duration', required=True)
    unit = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month')],
        string='Unit', required=True)
    pricing_ids = fields.One2many('rental.pricing', 'period_id', string='Pricing')

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Rental Period Name must be unique!'),
    ]
