from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class PickupOrderWizard(models.TransientModel):
    _name = 'pickup.order.wizard'
    _description = 'Pickup Order Wizard'

    pickup_date = fields.Date(string='Pickup Date', required=True)
    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    line_ids = fields.One2many('pickup.order.wizard.line', 'wizard_id', string='Order Lines')

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
            lines = []
            for line in order_lines:
                lines.append((0, 0, {
                    'rental_stock_id': line.id,
                    'quantity_to_pickup': 0,
                }))
            self.line_ids = lines

    def action_pickup_order(self):
        for line in self.line_ids:
            if line.quantity_to_pickup <= 0:
                continue  # Skip lines with zero or negative pickup quantity

            if line.quantity_to_pickup > line.quantity_reserved:
                raise exceptions.ValidationError('Quantity to Pickup cannot exceed Reserved Quantity.')

            # Update reserved quantity and rented quantity in rental stock
            line.rental_stock_id.write({
                'reserved_qty': line.rental_stock_id.reserved_qty - line.quantity_to_pickup,
                'rented_qty': line.rental_stock_id.rented_qty + line.quantity_to_pickup,
            })

        # Check if all rental stock lines for the order have zero reserved quantity
        order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
        all_reserved_zero = all(line.reserved_qty == 0 for line in order_lines)
        if all_reserved_zero:
            self.order_id.write({'state': 'rented'})


class PickupOrderLineWizard(models.TransientModel):
    _name = 'pickup.order.wizard.line'
    _description = 'Pickup Order Wizard Line'

    wizard_id = fields.Many2one('pickup.order.wizard', string='Wizard')
    rental_stock_id = fields.Many2one('rental.stock', string='Rental Stock', required=True)
    quantity_reserved = fields.Float(string='Reserved Quantity', compute='_compute_quantity_reserved')
    quantity_to_pickup = fields.Float(string='Quantity to Pickup')

    @api.depends('rental_stock_id')
    def _compute_quantity_reserved(self):
        for line in self:
            line.quantity_reserved = line.rental_stock_id.reserved_qty

    @api.onchange('rental_stock_id')
    def _onchange_rental_stock_id(self):
        if self.rental_stock_id:
            self.quantity_to_pickup = self.quantity_reserved

    @api.constrains('quantity_to_pickup')
    def _check_quantity_to_pickup(self):
        for line in self:
            if line.quantity_to_pickup < 0:
                raise exceptions.ValidationError('Quantity to Pickup cannot be negative.')
            if line.quantity_to_pickup > line.quantity_reserved:
                raise exceptions.ValidationError('Quantity to Pickup cannot exceed Reserved Quantity.')
