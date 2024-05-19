from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, exceptions


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, size=64)

    rental_start_date = fields.Datetime(string='Rental Start Date')
    rental_end_date = fields.Datetime(string='Rental End Date')
    rental_return_date = fields.Datetime(string='Rental Return Date')
    rental_reservation_ids = fields.One2many('rental.reservation', 'order_id', string='Rental Reservations')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('reserved', 'Reserved'),
        ('rented', 'Rented')
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    def action_confirm(self):
        res = super(RentalOrder, self).action_confirm()
        self.write({'state': 'reserved'})  # Change to 'reserved' instead of 'sale' to follow rental workflow
        return res

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
        self.ensure_one()

        # Ensure the order is in the 'reserved' state
        if self.state != 'reserved':
            raise exceptions.UserError('Order must be in reserved state to pick up.')

        # Initialize a dictionary to store picked up quantities per product
        picked_up_quantities = {}

        # Retrieve reservations for the order's products
        for line in self.order_line:
            reservation = self.env['rental.reservation'].search([
                ('order_id', '=', self.id),
                ('product_id', '=', line.product_id.id)
            ], limit=1)

            # Update quantity reserved and quantity delivered
            if reservation:
                reservation.write({
                    'quantity_reserved': reservation.quantity_reserved - line.product_uom_qty,
                    'quantity_delivered': reservation.quantity_delivered + line.product_uom_qty,
                })

            # Update picked up quantities dictionary
            if line.product_id.id in picked_up_quantities:
                picked_up_quantities[line.product_id.id] += line.product_uom_qty
            else:
                picked_up_quantities[line.product_id.id] = line.product_uom_qty

        # Update on_rent quantities for picked up products
        for product_id, picked_up_qty in picked_up_quantities.items():
            product = self.env['product.product'].browse(product_id)
            product.write({'on_rent': product.on_rent + picked_up_qty})

        # Update order state to 'rented' or any appropriate state
        self.write({'state': 'rented'})

        return True

    def action_return_order(self):
        self.ensure_one()

        # Ensure the order is in the 'rented' state
        if self.state != 'rented':
            raise exceptions.UserError('Order must be in rented state to return.')

        # Initialize a dictionary to store returned quantities per product
        returned_quantities = {}

        # Retrieve reservations for the order's products
        for line in self.order_line:
            reservation = self.env['rental.reservation'].search([
                ('order_id', '=', self.id),
                ('product_id', '=', line.product_id.id)
            ], limit=1)

            # Update quantity reserved and quantity delivered
            if reservation:
                reservation.write({
                    'quantity_reserved': reservation.quantity_reserved + line.product_uom_qty,
                    'quantity_delivered': reservation.quantity_delivered - line.product_uom_qty,
                })

            # Update returned quantities dictionary
            if line.product_id.id in returned_quantities:
                returned_quantities[line.product_id.id] += line.product_uom_qty
            else:
                returned_quantities[line.product_id.id] = line.product_uom_qty

        # Update on-hand quantities for returned products
        for product_id, returned_qty in returned_quantities.items():
            product = self.env['product.product'].browse(product_id)
            product.write({'on_rent': product.on_rent - returned_qty})

        # Update order state to 'done' or any appropriate state
        self.write({'state': 'done'})

        return True

    @api.depends('order_line.price_total', 'order_line.rental_price')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = rental_price = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                rental_price += line.rental_price
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax + rental_price,
            })

    def reset_dates(self):
        for line in self.order_line:
            line.rental_start_date = self.rental_start_date
            line.rental_end_date = self.rental_end_date

    @api.model
    def create(self, values):
        """
        Override the create method to handle rental product reservations.
        """
        if 'order_line' in values:
            order_lines = values['order_line']
            rental_products = []
            for line in order_lines:
                product_id = line[2].get('product_id')
                product = self.env['product.product'].browse(product_id)
                if product.can_be_rented:
                    rental_products.append({
                        'product_id': product_id,
                        'quantity': line[2].get('product_uom_qty'),
                        'start_date': values.get('rental_start_date'),
                        'end_date': values.get('rental_end_date')
                    })
            if rental_products:
                values['rental_reservation_ids'] = [(0, 0, rental) for rental in rental_products]
        return super(RentalOrder, self).create(values)

    # @api.model
    # def create(self, values):
    #     if 'state' not in values:
    #         values['state'] = 'draft'
    #     return super(RentalOrder, self).create(values)


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_start_date = fields.Datetime(related='order_id.rental_start_date', string='Rental Start Date', store=True,
                                        readonly=False)
    rental_end_date = fields.Datetime(related='order_id.rental_end_date', string='Rental End Date', store=True,
                                      readonly=False)
    rental_return_date = fields.Datetime(related='order_id.rental_return_date', string='Rental Return Date', store=True,
                                         readonly=False)
    rental_pricing_id = fields.Many2one('rental.pricing', string='Rental Pricing')

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
