# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TransferCost(models.TransientModel):
    _name = "transfer.cost"
    _description = "Transfer value of some field to another field in product"

    categ_id = fields.Many2one('product.category', 'Internal Category',
                               required=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 domain="[('categ_id', 'child_of', categ_id)]")
    transfer_operation = fields.Selection(
        [('last_po_cost_to_lp_base', '"Last PO cost" to "LP base"'),
         ('lp_base_to_cost', '"LP base" to "Cost"'),
         ('last_po_cost_to_cost', '"Last PO cost" to "Cost"')],
        string='Transfer options', required=True)

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        self.product_id = False

    @api.multi
    def execute(self):
        """ Button action function for transfer values from some field to
        another field, based on option selected
        """
        self.ensure_one()

        products = self.env['product.product']
        child_domain = [('categ_id', 'child_of', self.categ_id.id)]
        if self.product_id:
            domain = [('id', '=', self.product_id.id)]

            products = products.search(domain + child_domain)

            # ensure to created product on the fly belong to correct category
            if not len(products):
                raise ValidationError(_("If you select a product, it should "
                                        "belongs to a descending category of "
                                        "the selected category"))
        else:
            products = products.search(child_domain)

        transfer_fields = {
            'last_po_cost_to_lp_base': ('last_po_cost', 'lp_base'),
            'lp_base_to_cost': ('lp_base', 'cost'),
            'last_po_cost_to_cost': ('last_po_cost', 'cost')
        }
        for product in products:
            str_from, str_to = transfer_fields[self.transfer_operation]
            product[str_to] = product[str_from]
