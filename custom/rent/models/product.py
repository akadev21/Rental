from odoo import models, fields, api


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

    @property
    def rental_stock_count(self):
        return sum(self.rental_stock_ids.filtered(lambda stock: stock.product_id == self).mapped('rented_qty'))

    on_rent = fields.Integer(compute='_compute_on_rent', string='On Rent', store=True)

    @api.depends('rental_stock_ids.rented_qty')
    def _compute_on_rent(self):
        for product in self:
            product.on_rent = product.rental_stock_count


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
