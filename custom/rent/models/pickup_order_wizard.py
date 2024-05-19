from odoo import models, fields, api, exceptions


class PickupOrderWizard(models.TransientModel):
    _name = 'pickup.order.wizard'
    _description = 'Pickup Order Wizard'

    pickup_date = fields.Datetime(string="Pickup Date", default=fields.Datetime.now)
    order_id = fields.Many2one('sale.order', string='Order', required=True)
    line_ids = fields.One2many('pickup.order.wizard.line', 'wizard_id', string='Order Lines')

    @api.model
    def default_get(self, fields):
        res = super(PickupOrderWizard, self).default_get(fields)
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
                    'quantity_reserved': reservation.quantity_reserved
                }))
            res.update({
                'order_id': order_id,
                'line_ids': lines
            })
        return res

    def action_pickup_order(self):
        self.ensure_one()

        # Ensure the order is in the 'reserved' state
        if self.order_id.state != 'reserved':
            raise exceptions.UserError('Order must be in reserved state to pick up.')

        for line in self.line_ids:
            reservation = self.env['rental.reservation'].search([
                ('order_id', '=', self.order_id.id),
                ('product_id', '=', line.product_id.id)
            ], limit=1)

            if reservation:
                reservation.write({
                    'quantity_reserved': reservation.quantity_reserved - line.quantity_reserved,
                    'quantity_delivered': reservation.quantity_delivered + line.quantity_reserved,
                })

        # Update 'on_rent' for each product
        for line in self.line_ids:
            product = line.product_id
            product.on_rent += line.quantity_reserved

        # Update order state to 'rented'
        self.order_id.write({'state': 'rented'})

        return True


class PickupOrderWizardLine(models.TransientModel):
    _name = 'pickup.order.wizard.line'
    _description = 'Pickup Order Wizard Line'

    wizard_id = fields.Many2one('pickup.order.wizard', string="Wizard", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity_reserved = fields.Float(string="Quantity Reserved", required=True)
