from odoo import models, fields, api, exceptions
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, size=64)
    product_id = fields.Many2one('product.product', string='Product', related='order_line.product_id')
    rental_start_date = fields.Datetime(string='Rental Start Date', default=lambda self: fields.Datetime.now())
    rental_end_date = fields.Datetime(string='Rental End Date', default=lambda self: fields.Datetime.now())
    rental_return_date = fields.Datetime(string='Rental Return Date')
    rental_reservation_ids = fields.One2many('rental.reservation', 'order_id', string='Rental Reservations')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Done'),
        ('reserved', 'Reserved'),
        ('cancel', 'Cancelled'),
        ('rented', 'Rented'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    stage = fields.Selection([
        ('reserved', 'Reserved'),
        ('picked_up', 'Picked Up'),
        ('returned', 'Returned'),
    ], string='Stage', default='reserved', readonly=True)

    def mark_as_done(self):
        for order in self:
            order.write({'state': 'done'})
            order.unreserve_products()

    def unreserve_products(self):
        for line in self.order_line:
            rental_stock = self.env['rental.stock'].search([
                ('product_id', '=', line.product_id.id),
                ('order_id', '=', self.id),
            ], limit=1)
            if rental_stock:
                rental_stock.update_stock(reserved_qty_change=-line.product_uom_qty)

    @api.model
    def create(self, values):
        if 'order_line' in values:
            rental_products = []
            for line in values.get('order_line'):
                product_id = line[2].get('product_id')
                product = self.env['product.product'].browse(product_id)
                if product.can_be_rented:
                    rental_products.append({
                        'product_id': product_id,
                        'quantity_reserved': line[2].get('product_uom_qty'),
                        'start_date': values.get('rental_start_date'),
                        'end_date': values.get('rental_end_date')
                    })
            if rental_products:
                values['rental_reservation_ids'] = [(0, 0, rental) for rental in rental_products]

        # Set default state to 'draft' if not provided
        values.setdefault('state', 'draft')

        return super(RentalOrder, self).create(values)

    def action_quotation_send(self):
        self.ensure_one()
        self.write({'state': 'sent'})
        return super(RentalOrder, self).action_quotation_send()

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_pickup_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pickup Order',
            'res_model': 'pickup.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_return_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Order',
            'res_model': 'return.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_confirm(self):
        res = super(RentalOrder, self).action_confirm()
        self.write({'state': 'reserved'})
        self.prepare_rental_stock()
        return res

    def prepare_rental_stock(self):
        rental_stock = self.env['rental.stock']
        for line in self.order_line:
            stock_record = rental_stock.search(
                [('product_id', '=', line.product_id.id), ('order_id', '=', self.id)], limit=1)
            if not stock_record:
                rental_stock.create({
                    'product_id': line.product_id.id,
                    'order_id': self.id,
                    'reserved_qty': line.product_uom_qty - line.qty_delivered,
                    'rented_qty': 0,
                    'returned_qty': 0
                })
            else:
                stock_record.write({
                    'reserved_qty': stock_record.reserved_qty + line.product_uom_qty - line.qty_delivered
                })

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.rental_price',
                 'order_line.extra_charge')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = rental_price = extra_charge = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                rental_price += line.rental_price
                extra_charge += line.extra_charge

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax + rental_price + extra_charge,
            })

    @api.constrains('rental_start_date', 'rental_end_date')
    def _check_rental_dates(self):
        for order in self:
            if order.rental_end_date and order.rental_start_date:
                if order.rental_end_date < order.rental_start_date:
                    raise exceptions.ValidationError("The rental end date cannot be before the start date.")

    def reset_dates(self):
        for line in self.order_line:
            line.rental_start_date = self.rental_start_date
            line.rental_end_date = self.rental_end_date


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_start_date = fields.Datetime(
        default=fields.Datetime.now,
        string='Rental Start Date',
        store=True,
        readonly=False)
    rental_end_date = fields.Datetime(
        default=fields.Datetime.now,
        string='Rental End Date',
        store=True,
        readonly=False)
    rental_pricing_id = fields.Many2one('rental.pricing', string='Rental Pricing')
    rental_months = fields.Integer(string='Rental Months', compute='_compute_rental_breakdown', store=True)
    rental_weeks = fields.Integer(string='Rental Weeks', compute='_compute_rental_breakdown', store=True)
    rental_days = fields.Integer(string='Rental Days', compute='_compute_rental_breakdown', store=True)
    rental_hours = fields.Integer(string='Rental Hours', compute='_compute_rental_breakdown', store=True)
    extra_hour = fields.Float(related='product_id.extra_hour', string='Extra Hour Charge', readonly=True)
    extra_day = fields.Float(related='product_id.extra_day', string='Extra Day Charge', readonly=True)
    late_days = fields.Integer(string='Late Days', compute='_compute_late_period_breakdown')
    late_hours = fields.Integer(string='Late Hours', compute='_compute_late_period_breakdown')
    extra_charge = fields.Float(string='Extra Charge', compute='_compute_extra_charge')
    on_return_date = fields.Datetime(related='product_id.on_return_date', string='On Return Date')
    return_date = fields.Datetime(compute='_compute_return_date', string='Return Date')

    @api.depends('order_id', 'product_id')
    def _compute_return_date(self):
        for line in self:
            rental_stock = self.env['rental.stock'].search([
                ('order_id', '=', line.order_id.id),
                ('product_id', '=', line.product_id.id),
                ('return_date', '!=', False)
            ], limit=1)
            line.return_date = rental_stock.return_date if rental_stock else False

    @api.depends('on_return_date', 'rental_end_date', 'return_date')
    def _compute_late_period_breakdown(self):
        for line in self:
            line.late_days = 0
            line.late_hours = 0

            if line.return_date and line.rental_end_date:
                if line.return_date > line.rental_end_date:
                    duration = relativedelta(line.return_date, line.rental_end_date)
                    line.late_days = duration.days
                    line.late_hours = duration.hours

    @api.depends('late_hours', 'late_days', 'extra_hour', 'extra_day')
    def _compute_extra_charge(self):
        for line in self:
            extra_charge = (line.late_hours * line.extra_hour) + (line.late_days * line.extra_day)
            line.extra_charge = extra_charge

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

    @api.depends('rental_hours', 'rental_days', 'rental_weeks', 'rental_months', 'product_id',
                 'product_uom_qty')
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
                raise exceptions.ValidationError(
                    'The quantity cannot exceed the available quantity for this product.')
   