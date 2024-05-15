from odoo import models, fields, api, exceptions
import logging
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    rental_start_date = fields.Datetime(string='Rental Start Date')
    rental_end_date = fields.Datetime(string='Rental End Date')
    rental_return_date = fields.Datetime(string='Rental Return')
    rental_reservation_ids = fields.One2many('rental.reservation', 'order_id', string='Rental Reservations')

    def reset_dates(self):
        for line in self.order_line:
            line.rental_start_date = self.rental_start_date
            line.rental_end_date = self.rental_end_date

    @api.model
    def create(self, values):
        if 'order_line' in values:
            order_lines = values['order_line']
            rental_products = []
            for line in order_lines:
                product_id = line[2].get('product_id')
                product = self.env['product.product'].browse(product_id)
                if product.can_be_rented:
                    rental_products.append({
                        'product_id': product_id,
                        'qty': line[2].get('product_uom_qty'),
                        'start_date': values.get('rental_start_date'),
                        'end_date': values.get('rental_end_date')
                    })
            if rental_products:
                values['rental_reservation_ids'] = [(0, 0, rental) for rental in rental_products]
        return super(RentalOrder, self).create(values)


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_start_date = fields.Datetime(related='order_id.rental_start_date', string='Rental Start Date', store=True,
                                        readonly=False)
    rental_end_date = fields.Datetime(related='order_id.rental_end_date', string='Rental End Date', store=True,
                                      readonly=False)
    rental_return_date = fields.Datetime(related='order_id.rental_return_date', string='Rental Return Date', store=True,
                                         readonly=False)
    # rental_price = fields.Float(string='Rental Price', compute='_compute_rental_price', store=True)

    rental_pricing_id = fields.Many2one('rental.pricing', string='Rental Pricing')

    # price for different Units
    rental_months = fields.Integer(string='Rental Months', compute='_compute_rental_breakdown', store=True)
    rental_weeks = fields.Integer(string='Rental Weeks', compute='_compute_rental_breakdown', store=True)
    rental_days = fields.Integer(string='Rental Days', compute='_compute_rental_breakdown', store=True)
    rental_hours = fields.Integer(string='Rental Hours', compute='_compute_rental_breakdown', store=True)

    @api.depends('rental_start_date', 'rental_end_date')
    def _compute_rental_breakdown(self):
        for line in self:
            if line.rental_start_date and line.rental_end_date:
                duration = relativedelta(line.rental_end_date, line.rental_start_date)

                line.rental_months = duration.years * 12 + duration.months
                line.rental_weeks = duration.days // 7
                line.rental_days = duration.days % 7
                line.rental_hours = duration.hours

    rental_price = fields.Float(string='Rental Price', compute='_compute_rental_price', store=True)

    @api.depends('rental_hours', 'rental_days', 'rental_weeks', 'rental_months', 'product_id', 'product_uom_qty')
    def _compute_rental_price(self):
        for line in self:
            rental_price = 0.0

            pricing_records = line.env['rental.pricing'].search([
                ('product_template_id', '=', line.product_id.product_tmpl_id.id)
            ])

            for pricing in pricing_records:
                if pricing.period_id.unit == 'hour' and line.rental_hours:
                    rental_price += pricing.price * line.rental_hours
                elif pricing.period_id.unit == 'day' and line.rental_days:
                    rental_price += pricing.price * line.rental_days
                elif pricing.period_id.unit == 'week' and line.rental_weeks:
                    rental_price += pricing.price * line.rental_weeks
                elif pricing.period_id.unit == 'month' and line.rental_months:
                    rental_price += pricing.price * line.rental_months

            line.rental_price = rental_price * line.product_uom_qty


    @api.constrains('product_id', 'product_uom_qty')
    def check_quantity(self):
        for line in self:
            if line.product_id.can_be_rented and line.product_uom_qty > line.product_id.qty_available:
                raise exceptions.ValidationError('The quantity cannot exceed the available quantity for this product.')
