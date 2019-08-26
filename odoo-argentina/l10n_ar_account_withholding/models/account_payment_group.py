# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, api, fields


class AccountPaymentGroup(models.Model):

    _inherit = "account.payment.group"

    # @api.model
    # def _get_regimen_ganancias(self):
    #     result = []
    #     for line in self.
    #     return

    retencion_ganancias = fields.Selection([
        # _get_regimen_ganancias,
        ('imposibilidad_retencion', 'Imp de Ret'),
        ('no_aplica', 'No Aplica'),
        ('nro_regimen', 'Nro Regimen'),
    ],
        'Retencion Ganancias',
        readonly=True,
        states={'draft': [('readonly', False)],
                'confirmed': [('readonly', False)]}
    )
    regimen_ganancias_id = fields.Many2many('afip.tabla_ganancias.alicuotasymontos','afip_tab_rel','tab_1','afip_1',
        'Regimen Ganancias',
        readonly=True,
        ondelete='restrict',
        states={'draft': [('readonly', False)],
                'confirmed': [('readonly', False)]}
    )
    company_regimenes_ganancias_ids = fields.Many2many(
        related='company_id.regimenes_ganancias_ids',
        readonly=True,
    )

    @api.onchange('retencion_ganancias', 'commercial_partner_id')
    def change_retencion_ganancias(self):
        def_regimen = False
        if self.retencion_ganancias == 'nro_regimen':
            cia_regs = self.company_regimenes_ganancias_ids
            partner_regimen = (self.commercial_partner_id.default_regimen_ganancias_id)
            foundf = False
            if partner_regimen:
                for reg in partner_regimen:
                    if reg in cia_regs:
                        foundf = True
            if foundf:
                self.regimen_ganancias_id = partner_regimen

    @api.onchange('company_regimenes_ganancias_ids')
    def change_company_regimenes_ganancias(self):
        if (self.company_regimenes_ganancias_ids and self.partner_type == 'supplier'):
            self.retencion_ganancias = 'nro_regimen'

    @api.onchange('commercial_partner_id')
    def on_change_commercial_partner_id_retencion_g(self):
        foundf = False
        cia_regs = self.company_regimenes_ganancias_ids
        partner_regimen = (self.commercial_partner_id.default_regimen_ganancias_id)
        if (self.company_regimenes_ganancias_ids and self.partner_type == 'supplier'):
            for reg in partner_regimen:
                if reg in cia_regs:
                    foundf = True
        if foundf:
            self.retencion_ganancias = 'nro_regimen'
        else:
            self.retencion_ganancias = 'no_aplica'

    #@api.model
    #def create(self, vals):
        #"""
        #para casos donde se paga desde algun otro lugar (por ej. liquidador de
        #impuestos), seteamos no aplica si no hay nada seteado
        #"""
        #payment_group = super(AccountPaymentGroup, self).create(vals)
        #return payment_group
