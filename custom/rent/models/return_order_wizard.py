from odoo import models, fields, api, exceptions


class ReturnOrderWizard(models.TransientModel):
    _name = 'return.order.wizard'
    _description = 'Return Order Wizard'

    return_date = fields.Datetime(string="Return Date", default=fields.Datetime.now)
    order_id = fields.Many2one('sale.order', string='Order', required=True)
    line_ids = fields.One2many('return.order.wizard.line', 'wizard_id', string='Order Lines')

    @api.model
    def default_get(self, fields):
        res = super(ReturnOrderWizard, self).default_get(fields)
        order_id = self.env.context.get('default_order_id')
        if order_id:
            order = self.env['sale.order'].browse(order_id)
            lines = []
            reservations = self.env['rental.reservation'].search([
                ('order_id', '=', order_id)
            ])
            for reservation in reservations:
                lines.append((0, 0, {
                    'product_id': reservation.product_id.id,
                    'quantity_delivered': reservation.quantity_delivered
                }))
            res.update({
                'order_id': order_id,
                'line_ids': lines
            })
        return res

    def action_return_order(self):
        self.ensure_one()

        # Ensure the order is in the 'rented' state
        if self.order_id.state != 'rented':
            raise exceptions.UserError('Order must be in rented state to return.')

        for line in self.line_ids:
            reservation = self.env['rental.reservation'].search([
                ('order_id', '=', self.order_id.id),
                ('product_id', '=', line.product_id.id)
            ], limit=1)

            if reservation:
                reservation.write({
                    'quantity_returned': reservation.quantity_returned + line.quantity_returned,
                    'quantity_delivered': reservation.quantity_delivered - line.quantity_returned,
                })

        # Update 'on_rent' for each product
        for line in self.line_ids:
            product = line.product_id
            product.on_rent -= line.quantity_returned

        # Update order state to 'returned'
        self.order_id.write({'state': 'done'})

        return True


class ReturnOrderWizardLine(models.TransientModel):
    _name = 'return.order.wizard.line'
    _description = 'Return Order Wizard Line'

    wizard_id = fields.Many2one('return.order.wizard', string="Wizard", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity_returned = fields.Float(string="Quantity Returned", required=True)
