from odoo import models, fields, api, exceptions

class PickupOrderWizard(models.TransientModel):
    _name = 'pickup.order.wizard'
    _description = 'Pickup Order Wizard'

    def _default_order(self):
        return self.env['sale.order'].browse(self._context.get('active_id'))

    order_id = fields.Many2one('sale.order', string='Order', default=_default_order, readonly=True)
    pickup_date = fields.Datetime(string='Pickup Date', required=True)

    def action_pickup_order(self):
        self.ensure_one()
        if self.order_id.state != 'reserved':
            raise exceptions.UserError('You can only pick up orders that are in the "Reserved" state.')
        self.order_id.write({'state': 'rented', 'rental_return_date': self.pickup_date})
        return {'type': 'ir.actions.act_window_close'}