from odoo import models, fields, api, exceptions


class ReturnOrderWizard(models.TransientModel):
    _name = 'return.order.wizard'
    _description = 'Return Order Wizard'

    return_date = fields.Date(string='Return Date', required=True)
    order_id = fields.Many2one('sale.order', string='Order Reference', required=True)
    line_ids = fields.One2many('return.order.wizard.line', 'wizard_id', string='Order Lines')

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

            if line.quantity_to_return > line.rental_stock_id.rented_qty:
                raise exceptions.ValidationError('Quantity to Return cannot exceed Rented Quantity.')

            # Update rented quantity in rental stock
            line.rental_stock_id.write({
                'rented_qty': line.rental_stock_id.rented_qty - line.quantity_to_return,
            })

        # Check if all rental stock lines for the order have zero rented quantity
        order_lines = self.env['rental.stock'].search([('order_id', '=', self.order_id.id)])
        all_rented_zero = all(line.rented_qty == 0 for line in order_lines)
        if all_rented_zero:
            self.order_id.write({'state': 'returned'})


class ReturnOrderWizardLine(models.TransientModel):
    _name = 'return.order.wizard.line'
    _description = 'Return Order Wizard Line'

    wizard_id = fields.Many2one('return.order.wizard', string='Wizard')
    rental_stock_id = fields.Many2one('rental.stock', string='Rental Stock', required=True)
    quantity_to_return = fields.Float(string='Quantity to Return')
    quantity_rented = fields.Float(string='Quantity Rented', related='rental_stock_id.rented_qty', readonly=True)

    @api.onchange('rental_stock_id')
    def _onchange_rental_stock_id(self):
        if self.rental_stock_id:
            # Set the default quantity to return to the maximum available quantity
            self.quantity_to_return = self.rental_stock_id.rented_qty

    @api.constrains('quantity_to_return')
    def _check_quantity_to_return(self):
        for line in self:
            if line.quantity_to_return < 0:
                raise exceptions.ValidationError('Quantity to Return cannot be negative.')
            if line.quantity_to_return > line.rental_stock_id.rented_qty:
                raise exceptions.ValidationError('Quantity to Return cannot exceed Rented Quantity.')
