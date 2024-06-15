from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class ReturnOrderWizard(models.TransientModel):
    _name = 'return.order.wizard'
    _description = 'Return Order Wizard'

    return_date = fields.Datetime(string='Return Date', required=True)
    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    line_ids = fields.One2many('return.order.wizard.line', 'wizard_id', string='Order Lines')
    reservation_id = fields.Many2one('rental.reservation', string='Rental Reservation')

    def confirm_return(self):
        self.ensure_one()
        _logger.info("Confirming return for order %s with return date: %s", self.order_id.id, self.return_date)

        # Update the return date on the sale.order
        self.order_id.write({'rental_return_date': self.return_date})
        _logger.info("Updated rental_return_date on sale.order %s to: %s", self.order_id.id, self.return_date)

        # Update return date on related rental stock items
        self.update_rental_stock_return_date()

        return {'type': 'ir.actions.act_window_close'}

    def update_rental_stock_return_date(self):
        for line in self.line_ids:
            _logger.info("Updating return date for rental.stock %s to: %s", line.rental_stock_id.id, self.return_date)
            line.rental_stock_id.write({'return_date': self.return_date})
            _logger.info("Updated return_date for rental.stock %s to: %s", line.rental_stock_id.id, self.return_date)

    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
            lines = []
            for line in order_lines:
                lines.append((0, 0, {
                    'rental_stock_id': line.id,
                    'quantity_to_return': 0,
                }))
            self.line_ids = lines

    def action_return_order(self):
        for line in self.line_ids:
            if line.quantity_to_return <= 0:
                continue  # Skip lines with zero or negative return quantity

            if line.quantity_to_return > line.quantity_rented:
                raise exceptions.ValidationError('Quantity to Return cannot exceed Rented Quantity.')

            # Update rented quantity and returned quantity in rental stock, including return_date
            line.rental_stock_id.write({
                'rented_qty': line.rental_stock_id.rented_qty - line.quantity_to_return,
                'returned_qty': line.rental_stock_id.returned_qty + line.quantity_to_return,
                'return_date': self.return_date,  # Assuming return_date is a field in ReturnOrderWizard
            })

        # Check if all rental stock lines for the order have zero rented quantity
        order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
        all_rented_zero = all(line.rented_qty == 0 for line in order_lines)
        if all_rented_zero:
            self.order_id.write({'state': 'done'})

        return {'type': 'ir.actions.act_window_close'}

class ReturnOrderWizardLine(models.TransientModel):
    _name = 'return.order.wizard.line'
    _description = 'Return Order Wizard Line'

    wizard_id = fields.Many2one('return.order.wizard', string='Wizard')
    rental_stock_id = fields.Many2one('rental.stock', string='Rental Stock', required=True)
    quantity_rented = fields.Float(string='Rented Quantity', compute='_compute_quantity_rented')
    quantity_to_return = fields.Float(string='Quantity to Return')

    @api.depends('rental_stock_id')
    def _compute_quantity_rented(self):
        for line in self:
            line.quantity_rented = line.rental_stock_id.rented_qty

    @api.onchange('rental_stock_id')
    def _onchange_rental_stock_id(self):
        if self.rental_stock_id:
            self.quantity_to_return = self.quantity_rented

    @api.constrains('quantity_to_return')
    def _check_quantity_to_return(self):
        for line in self:
            if line.quantity_to_return < 0:
                raise exceptions.ValidationError('Quantity to Return cannot be negative.')
            if line.quantity_to_return > line.quantity_rented:
                raise exceptions.ValidationError('Quantity to Return cannot exceed Rented Quantity.')
