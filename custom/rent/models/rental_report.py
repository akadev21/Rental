from odoo import tools
from odoo import api, fields, models


class RentalReport(models.Model):
    _name = "rental.report"
    _description = "Rental Analysis Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    name = fields.Char('Order Reference', readonly=True)
    date = fields.Datetime('Order Date', readonly=True)
    product_id = fields.Many2one('product.product', 'Product Variant', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    product_uom_qty = fields.Float('Qty Ordered', readonly=True)
    qty_delivered = fields.Float('Qty Delivered', readonly=True)
    qty_to_invoice = fields.Float('Qty To Invoice', readonly=True)
    qty_invoiced = fields.Float('Qty Invoiced', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    price_total = fields.Float('Total', readonly=True)
    price_subtotal = fields.Float('Untaxed Total', readonly=True)
    rental_start_date = fields.Datetime('Rental Start Date', readonly=True)
    rental_end_date = fields.Datetime('Rental End Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sale Order'),
        ('done', 'Locked'),
        ('reserved', 'Reserved'),
        ('cancel', 'Cancelled'),
        ('rented', 'Rented'),
    ], string='Status', readonly=True)

    def _select(self):
        return """
            SELECT
                min(l.id) as id,
                s.name as name,
                s.date_order as date,
                l.product_id as product_id,
                l.product_uom as product_uom,
                sum(l.product_uom_qty) as product_uom_qty,
                sum(l.qty_delivered) as qty_delivered,
                sum(l.qty_to_invoice) as qty_to_invoice,
                sum(l.qty_invoiced) as qty_invoiced,
                s.partner_id as partner_id,
                s.company_id as company_id,
                s.user_id as user_id,
                sum(l.price_total) as price_total,
                sum(l.price_subtotal) as price_subtotal,
                s.rental_start_date as rental_start_date,
                s.rental_end_date as rental_end_date,
                s.state as state
        """

    def _from(self):
        return """
            FROM sale_order_line l
            JOIN sale_order s ON l.order_id = s.id
        """

    def _group_by(self):
        return """
            GROUP BY
                s.name, s.date_order, l.product_id, l.product_uom, s.partner_id,
                s.company_id, s.user_id, s.rental_start_date, s.rental_end_date, s.state
        """

    def _query(self):
        return f"{self._select()} {self._from()} WHERE l.display_type IS NULL {self._group_by()}"

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"CREATE VIEW {self._table} AS ({self._query()})")
