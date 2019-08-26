# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
# import odoo.addons.decimal_precision as dp
# import re
from odoo.tools.misc import formatLang
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    """
    about name_get and display name:
    * in this model name_get and name_search are re-defined so we overwrite
    them
    * we add display_name to replace name field use, we add
     with search funcion. This field is used then for name_get and name_search

    Acccoding this https://www.odoo.com/es_ES/forum/ayuda-1/question/
    how-to-override-name-get-method-in-new-api-61228
    we should modify name_get, we do that by creating a helper display_name
    field and also overwriting name_get to use it
    """
    _inherit = "account.invoice"
    _order = "document_number desc, number desc, id desc"

    report_amount_tax = fields.Monetary(
        string='Tax',
        compute='_compute_report_amount_and_taxes'
    )
    report_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_report_amount_and_taxes'
    )
    report_tax_line_ids = fields.One2many(
        compute="_compute_report_amount_and_taxes",
        comodel_name='account.invoice.tax',
        string='Taxes'
    )
    available_journal_document_type_ids = fields.Many2many(
        'account.journal.document.type',
        compute='get_available_journal_document_types',
        string='Available Journal Document Types',
    )
    journal_document_type_id = fields.Many2one(
        'account.journal.document.type',
        'Document Type',
        readonly=True,
        ondelete='restrict',
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    # we add this fields so we can search, group and analyze by this one
    document_type_id = fields.Many2one(
        related='journal_document_type_id.document_type_id',
        copy=False,
        readonly=True,
        store=True,
    )
    document_sequence_id = fields.Many2one(
        related='journal_document_type_id.sequence_id',
        readonly=True,
    )
    document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    display_name = fields.Char(
        compute='_get_display_name',
        string='Document Reference',
    )
    next_number = fields.Integer(
        compute='_get_next_number',
        string='Next Number',
    )
    use_documents = fields.Boolean(
        related='journal_id.use_documents',
        string='Use Documents?',
        readonly=True
    )
    localization = fields.Selection(
        related='company_id.localization',
        readonly=True,
    )
    document_type_internal_type = fields.Selection(
        related='document_type_id.internal_type',
        readonly=True,
    )
    display_name2 = fields.Char(string='Document Reference')
    mipymesf = fields.Boolean(string="MiPymes")
    mipymesf_read_only = fields.Boolean(string="MiPymes",readonly=True)

    @api.model
    def _my_domain(self):
        return [('partner_id', '=', self.env.user.company_id.partner_id.id)]

    bank_account_id = fields.Many2one('res.partner.bank',string="Bank Account",translate=True,domain=_my_domain)
    cbu = fields.Char(string="Issuer CBU",translate=True)
    cbu_alias = fields.Char(string="Alias CBU")
    revocation_code = fields.Selection([('S','Es Anulacion'),('N','No es Anulacion')],string="Revocation Code",translate=True)
    internal_type = fields.Selection(related="journal_document_type_id.document_type_id.internal_type")
    comercial_ref = fields.Char(string="Commercial Reference",size=50)

    @api.onchange('journal_document_type_id','journal_id')
    def _onchange_journal_document_type_id(self):
        self.mipymesf = self.journal_document_type_id.document_type_id.mipymesf
        self.mipymesf_read_only = self.journal_document_type_id.document_type_id.mipymesf

    @api.onchange('bank_account_id')
    def _onchange_bank_account_id(self):
        self.cbu = self.bank_account_id.cbu
        self.cbu_alias = self.bank_account_id.cbu_alias

    @api.multi
    def _get_tax_amount_by_group2(self):
        self.ensure_one()
        res = {}
        currency = self.currency_id or self.company_id.currency_id
        for line in self.tax_line_ids:
            if not self.journal_document_type_id.document_type_id.document_letter_id.taxes_included:
                res.setdefault(line.tax_id.tax_group_id, 0.0)
                res[line.tax_id.tax_group_id] += line.amount
            else:
                if line.tax_id.tax_group_id.tax != 'vat':
                    res.setdefault(line.tax_id.tax_group_id, 0.0)
                    res[line.tax_id.tax_group_id] += line.amount
        res = sorted(res.items(), key=lambda l: l[0].sequence)
        res = map(lambda l: (l[0].name, formatLang(self.env, l[1], currency_obj=currency)), res)
        return res

    @api.multi
    @api.depends('amount_untaxed', 'amount_tax', 'tax_line_ids', 'document_type_id', 'invoice_line_ids')
    def _compute_report_amount_and_taxes(self):
        for invoice in self:
            for line in invoice.invoice_line_ids:
                invoice.report_amount_tax += line.report_price_subtotal
            invoice.report_amount_untaxed = invoice.amount_untaxed
            invoice.report_tax_line_ids = None

    @api.multi
    @api.depends(
        'journal_id.sequence_id.number_next_actual',
        'journal_document_type_id.sequence_id.number_next_actual',
    )
    def _get_next_number(self):
        """
        show next number only for invoices without number and on draft state
        """
        for invoice in self.filtered(
                lambda x: not x.display_name and x.state == 'draft'):
            if invoice.use_documents:
                sequence = invoice.journal_document_type_id.sequence_id
            elif (
                    invoice.type in ['out_refund', 'in_refund'] and
                    invoice.journal_id.refund_sequence
            ):
                sequence = invoice.journal_id.refund_sequence_id
            else:
                sequence = invoice.journal_id.sequence_id
            # we must check if sequence use date ranges
            if not sequence.use_date_range:
                invoice.next_number = sequence.number_next_actual
            else:
                dt = fields.Date.today()
                if self.env.context.get('ir_sequence_date'):
                    dt = self.env.context.get('ir_sequence_date')
                seq_date = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', sequence.id),
                    ('date_from', '<=', dt),
                    ('date_to', '>=', dt)], limit=1)
                if not seq_date:
                    seq_date = sequence._create_date_range_seq(dt)
                invoice.next_number = seq_date.number_next_actual

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            result.append((
                inv.id,
                "%s %s" % (
                    inv.display_name or TYPES[inv.type],
                    inv.name or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([
                '|', ('document_number', '=', name),
                ('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.one
    @api.constrains(
        'journal_id',
        'partner_id',
        'journal_document_type_id',
    )
    def _get_document_type(self):
        """ Como los campos responsible y journal document type no los
        queremos hacer funcion porque no queremos que sus valores cambien nunca
        y como con la funcion anterior solo se almacenan solo si se crea desde
        interfaz, hacemos este hack de constraint para computarlos si no estan
        computados"""
        if (
                not self.journal_document_type_id and
                self.available_journal_document_type_ids
        ):
            self.journal_document_type_id = (
                self._get_available_journal_document_types(
                    self.journal_id, self.type, self.partner_id
                ).get('journal_document_type'))

    @api.one
    @api.depends(
        'move_name',
        'document_number',
        'document_type_id.doc_code_prefix'
    )
    def _get_display_name(self):
        """
        If move_name then invoice has been validated, then:
        * If document number and document type, we show them
        * Else, we show move_name
        """
        if self.document_number and self.document_type_id and self.move_name:
            display_name = ("%s%s" % (
                self.document_type_id.doc_code_prefix or '',
                self.document_number))
        else:
            display_name = self.move_name
        self.display_name = display_name

    @api.multi
    def check_use_documents(self):
        """
        check invoices has document class but journal require it (we check
        all invoices, not only argentinian ones)
        """
        without_doucument_class = self.filtered(
            lambda r: (
                not r.document_type_id and r.journal_id.use_documents))
        if without_doucument_class:
            raise UserError(_(
                'Some invoices have a journal that require a document but not '
                'document type has been selected.\n'
                'Invoices ids: %s' % without_doucument_class.ids))

    @api.multi
    def get_localization_invoice_vals(self):
        """
        Function to be inherited by different localizations and add custom
        data to invoice on invoice validation
        """
        self.ensure_one()
        return {}

    @api.multi
    def action_move_create(self):
        """
        We add currency rate on move creation so it can be used by electronic
        invoice later on action_number
        """
        self.check_use_documents()
        res = super(AccountInvoice, self).action_move_create()
        self.set_document_data()
        return res

    @api.multi
    def set_document_data(self):
        """
        If journal document dont have any sequence, then document number
        must be set on the account.invoice and we use thisone
        A partir de este metodo no debería haber errores porque el modulo de
        factura electronica ya habria pedido el cae. Lo ideal sería hacer todo
        esto antes que se pida el cae pero tampoco se pueden volver a atras los
        conusmos de secuencias. TODO mejorar esa parte
        """
        # We write document_number field with next invoice number by
        # document type
        for invoice in self:
            _logger.info(
                'Setting document data on account.invoice and account.move')
            journal_document_type = invoice.journal_document_type_id
            inv_vals = invoice.get_localization_invoice_vals()
            if invoice.use_documents:
                if not invoice.document_number:
                    if not invoice.journal_document_type_id.sequence_id:
                        raise UserError(_(
                            'Error!. Please define sequence on the journal '
                            'related documents to this invoice or set the '
                            'document number.'))
                    document_number = (
                        journal_document_type.sequence_id.next_by_id())
                    inv_vals['document_number'] = document_number
                # for canelled invoice number that still has a document_number
                # if validated again we use old document_number
                # also use this for supplier invoices
                else:
                    document_number = invoice.document_number
                invoice.move_id.write({
                    'document_type_id': (
                        journal_document_type.document_type_id.id),
                    'document_number': document_number,
                })
            invoice.write(inv_vals)
        return True

    @api.multi
    @api.depends('journal_id', 'partner_id', 'company_id')
    def get_available_journal_document_types(self):
        """
        This function should only be inherited if you need to add another
        "depends", for eg, if you need to add a depend on "new_field" you
        should add:

        @api.depends('new_field')
        def _get_available_journal_document_types(
                self, journal, invoice_type, partner):
            return super(
                AccountInvoice, self)._get_available_journal_document_types(
                    journal, invoice_type, partner)
        """
        for invoice in self:
            if invoice.journal_id:
                res = invoice._get_available_journal_document_types(invoice.journal_id, invoice.type, invoice.partner_id)
                invoice.available_journal_document_type_ids = res['available_journal_document_types']
                invoice.journal_document_type_id = res['journal_document_type']
            else:
                invoice.available_journal_document_type_ids = None
                invoice.journal_document_type_id = None

    @api.multi
    @api.onchange('partner_id','journal_id')
    def _onchange_partner_id2(self):
      for invoice in self:
          invoice.get_available_journal_document_types()

    @api.multi
    @api.onchange('display_name','name','state')
    @api.constrains('display_name','name','state')
    def _onchange_display_name(self):
        for rec in self:
            rec.display_name2 = rec.display_name

    def _display_name_cron(self):
        invs = self.env['account.invoice'].search([])
        for invoice in invs:
            invoice.display_name2 = invoice.display_name
            invoice.write({'display_name2':invoice.display_name2})


    @api.onchange('partner_id','journal_id')
    def _onchange_partner_id3(self):
        if self.partner_id or self.journal_id:
            res = self._get_available_journal_document_types(self.journal_id, self.type, self.partner_id)

            return {'domain': {'journal_document_type_id': [('id', 'in', res['available_journal_document_types'].ids)]}}

    @api.model
    def _get_available_journal_document_types(
            self, journal, invoice_type, partner):
        """
        This function is to be inherited by differents localizations and MUST
        return a dictionary with two keys:
        * 'available_journal_document_types': available document types on
        this invoice
        * 'journal_document_type': suggested document type on this invoice
        """
        # As default we return every journal document type, and if one exists
        # then we return the first one as suggested
        journal_document_types = journal.journal_document_type_ids
        # if invoice is a refund only show credit_notes, else, not credit note
        if invoice_type in ['out_refund', 'in_refund']:
            journal_document_types = journal_document_types.filtered(
                lambda x: x.document_type_id.internal_type == 'credit_note')
        else:
            journal_document_types = journal_document_types.filtered(
                lambda x: x.document_type_id.internal_type != 'credit_note')
        journal_document_type = (
            journal_document_types and journal_document_types[0] or
            journal_document_types)
        return {
            'available_journal_document_types': journal_document_types,
            'journal_document_type': journal_document_type,
        }

    @api.multi
    @api.constrains('document_type_id', 'document_number')
    def validate_document_number(self):
        for rec in self:
            # if we have a sequence, number is set by sequence and we dont
            # check this
            if rec.document_sequence_id:
                continue
            document_type = rec.document_type_id

            if rec.document_type_id:
                res = document_type.validate_document_number(
                    rec.document_number)
                if res and res != rec.document_number:
                    rec.document_number = res

    @api.model
    def create(self, vals):
        if vals.get('mipymesf'):
            vals.update({'mipymesf_read_only': vals.get('mipymesf')})
        return super(AccountInvoice, self).create(vals)

