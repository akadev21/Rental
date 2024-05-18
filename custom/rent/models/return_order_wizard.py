from odoo import models, fields, api, exceptions


class ReturnOrderWizard(models.TransientModel):
    _name = 'return.order.wizard'
    _description = 'Return Order Wizard'

    def _default_order(self):
        return self.env['sale.order'].browse(self._context.get('active_id'))

    order_id = fields.Many2one('sale.order', string='Order', default=_default_order, readonly=True)
    return_date = fields.Datetime(string='Return Date', required=True)

    def action_return_order(self):
        self.ensure_one()
        if self.order_id.state != 'rented':
            raise exceptions.UserError('You can only return orders that are in the "Rented" state.')
        self.order_id.write({'state': 'done', 'rental_return_date': self.return_date})
        return {'type': 'ir.actions.act_window_close'}
