# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    def _make_duplicate_tags_message(self, duplicate_tags={}):
        msgstr = ''
        for dimension in duplicate_tags:
            msgstr += _('\n    * Dimension %s:\n' % (dimension))
            l = []
            for duplicate_tag in duplicate_tags[dimension]:
                l += ['        - %s: %s\n' % (duplicate_tag.code, duplicate_tag.name)]
            msgstr += ''.join(l)
        logstr = '\nAsset %s whith Problem. Duplicate Tags %s' % (self.asset_id.code, msgstr)
        _logger.error(logstr)
        return logstr

    @api.multi
    def show_message(self, msgstr):
        self.ensure_one()
        return self.env['account.asset.depreciation.wizard.message'].create({
            'exception_msg': msgstr,
            # 'partner_id': partner.id,
            'origin_reference': '%s,%s' % ('account.asset.asset', self.asset_id.id),
            'continue_method': 'action_confirm',
        }).action_show()

    def _move_update_analytic_tags(self, move, analytic_tags):
        res = False
        if move:
            account_move = self.env['account.move'].browse(move)
            for move in account_move:
                for move_line in move.line_ids:
                    if move_line.write({'analytic_tag_ids': [(6, 0, analytic_tags.ids)]}):
                        res = True

        return res

    @api.multi
    def create_move(self, post_move=True):
        res = []
        msgstr = ''
        for dep in self:
            move = None
            _logger.info('Processing Asset %s' % (dep.asset_id.code or dep.asset_id.name))
            ok_flag = False
            category_id = dep.asset_id.category_id
            analytic_tags = dep.env['account.analytic.tag']._set_tags(tags=dep.asset_id.analytic_tag_ids, new_tags=category_id.analytic_tag_ids + category_id.account_analytic_id.tag_ids)
            duplicate_tags = analytic_tags._check_duplicate_analytic_dimension() if analytic_tags else {}

            if analytic_tags:
                if not duplicate_tags:
                    move = super(AccountAssetDepreciationLine, dep).create_move(post_move=True)
                    ok_flag = self._move_update_analytic_tags(move, analytic_tags)
                else:
                    msgstr += self._make_duplicate_tags_message(duplicate_tags)
            else:
                move = super(AccountAssetDepreciationLine, dep).create_move(post_move=True)

            if ok_flag:
                _logger.info('Successful Asset %s' % (dep.asset_id.code or dep.asset_id.name))

            if move:
                if move[0] not in res:
                    res.append(move[0])

        if msgstr:
            self.show_message(msgstr)
        return res

    @api.multi
    def create_grouped_move(self, post_move=True):
        res = []
        msgstr = ''
        analytic_tag_obj = self.env['account.analytic.tag']
        depreciation_tags_ids = []
        for dep in self:
            move = None
            _logger.info('Processing Asset %s' % (dep.asset_id.code or dep.asset_id.name))
            category_id = dep.asset_id.category_id
            depreciation_tags_ids += category_id.analytic_tag_ids.ids + category_id.account_analytic_id.tag_ids.ids + dep.asset_id.analytic_tag_ids.ids

            depreciation_tags_ids = list(set(depreciation_tags_ids))
            depreciation_tags = analytic_tag_obj.browse(depreciation_tags_ids)
            analytic_tags = analytic_tag_obj._set_tags(tags=depreciation_tags, new_tags=depreciation_tags)
            duplicate_tags = analytic_tags._check_duplicate_analytic_dimension() if analytic_tags else {}
            if analytic_tags:
                if not duplicate_tags:
                    move = super(AccountAssetDepreciationLine, dep).create_grouped_move(post_move=False)
                else:
                    msgstr += dep._make_duplicate_tags_message(duplicate_tags)
            else:
                move = super(AccountAssetDepreciationLine, dep).create_grouped_move(post_move=False)

            if move:
                if move[0] not in res:
                    res.append(move[0])
        # if msgstr:
        #     self.show_message(msgstr)
        return res


class AccountAssetDepreciationMessage(models.TransientModel):
    _name = 'account.asset.depreciation.wizard.message'

    exception_msg = fields.Text(readonly=True)
    continue_method = fields.Char()
    origin_reference = fields.Reference(
        lambda self: [
            (m.model, m.name) for m in self.env['ir.model'].search([])],
        string='Object')

    @api.multi
    def action_show(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Warning'),
            'res_model': self._name,
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
