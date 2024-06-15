from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class RentalProductTemplate(models.Model):
    _description = 'Rental Product Template'
    _inherit = 'product.template'

    daily_price = fields.Float(string='Daily Rental Price')
    description_rent = fields.Text(string='Rental Description')
    can_be_rented = fields.Boolean(string='Can be Rented')
    period_id = fields.Many2one('rental.period', string='Rental Period')
    rental_pricing_ids = fields.One2many('rental.pricing', 'product_template_id',
                                         string='Rental Pricings')  # Added inverse field
    extra_hour = fields.Float(string='Extra Hour')
    extra_day = fields.Float(string='Extra Day')
    security_time = fields.Float(string='Security Time')

    quantity = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('maintenance', 'Maintenance')],
        string='Quantity', default='available')
    rental_stock_ids = fields.One2many('rental.stock', 'product_id', string='Rental Stock')

    on_rent = fields.Integer(compute='_compute_on_rent', string='On Rent')

    @api.depends('rental_stock_ids.rented_qty')
    def _compute_on_rent(self):
        for product in self:
            rental_stocks = self.env['rental.stock'].search([('product_id.product_tmpl_id', '=', product.id)])
            product.on_rent = sum(stock.rented_qty for stock in rental_stocks)

    on_reserve = fields.Integer(compute='_compute_on_reserve', string='On Reserve')

    @api.depends('rental_stock_ids.reserved_qty')
    def _compute_on_reserve(self):
        for product in self:
            rental_stocks = self.env['rental.stock'].search([
                ('product_id.product_tmpl_id', '=', product.id)
            ])
            product.on_reserve = sum(stock.reserved_qty for stock in rental_stocks)

    on_return_date = fields.Datetime(compute='_compute_on_return_date', string='On Return Date')

    @api.depends('rental_stock_ids.return_date')
    def _compute_on_return_date(self):
        for product in self:
            rental_stocks = self.env['rental.stock'].search([
                ('product_id.product_tmpl_id', '=', product.id),
                ('return_date', '!=', False)
            ])
            if rental_stocks:
                product.on_return_date = max(stock.return_date for stock in rental_stocks)
            else:
                product.on_return_date = False

class RentalProductProduct(models.Model):
    _description = 'Rental Product Product'
    _inherit = 'product.product'

    daily_price = fields.Float(related='product_tmpl_id.daily_price', string='Daily Rental Price', readonly=True)
    description_rent = fields.Text(related='product_tmpl_id.description_rent', string='Rental Description',
                                   readonly=True)
    can_be_rented = fields.Boolean(related='product_tmpl_id.can_be_rented', string='Can be Rented', readonly=True)
    period_id = fields.Many2one(related='product_tmpl_id.period_id', string='Rental Period', readonly=True)
    quantity = fields.Selection(related='product_tmpl_id.quantity', string='Quantity', readonly=True)
    rental_pricing_ids = fields.One2many(related='product_tmpl_id.rental_pricing_ids', string='Rental Price',
                                         readonly=True)
    extra_hour = fields.Float(related='product_tmpl_id.extra_hour', string='Extra Hour', readonly=True)
    extra_day = fields.Float(related='product_tmpl_id.extra_day', string='Extra Day', readonly=True)
    security_time = fields.Float(related='product_tmpl_id.security_time', string='Security Time', readonly=True)
    on_rent = fields.Integer(related='product_tmpl_id.on_rent', string='On Rent', readonly=True)
    on_reserve = fields.Integer(related='product_tmpl_id.on_reserve', string='On Reserve', readonly=True)
    on_return_date = fields.Datetime(related='product_tmpl_id.on_return_date', string='Last Return Date', readonly=True)
