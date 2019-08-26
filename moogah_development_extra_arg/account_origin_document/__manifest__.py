# -*- coding: utf-8 -*-
###############################################################################
#
#   account_origin_document for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2017-today Troova Software Development Group (troovacomercial@gmail.com).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

{
    'name': 'Origin Document',
    'description': """""",
    'author': 'Troova Software Development Group',
    'license': 'AGPL-3',
    'category': 'Account',
    'version': '10.0.1.0',
    'release_date': '2018-02-28',
    'summary': '',
    'depends': ['account_voucher', 'stock_account', 'account_payment_group',
                'vitt_cashin_cashout'],
    'data': [
        'views/account_move_view.xml',
        'views/account_invoice_view.xml',
        'views/account_payment_group_view.xml',
        'views/account_payment_widget.xml',
    ],
    'qweb': [
        "static/src/xml/account_payment.xml",
    ],
    'application': False,
}
