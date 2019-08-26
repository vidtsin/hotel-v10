# -*- coding: utf-8 -*-
##############################################################################
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'author': 'Moogah,ADHOC SA',
    'website': 'www.moogah.com',
    'license': 'AGPL-3',
    'category': 'Accounting & Finance',
    'data': [
        'views/account_tax_view.xml',
        'views/account_payment_group_view.xml',
        'views/account_payment_view.xml',
        'views/print_wh_cert_report.xml',
        'views/res_company_view.xml',
        'security/ir.model.access.csv',
        'wizards/withholding_automatic_wizard_views.xml',
    ],
    'demo': [
        'demo/withholding_demo.xml',
    ],
    'depends': [
        'account_payment_group',
        'account_withholding',
    ],
    'installable': True,
    'name': 'Retenciones Automáticas en Pagos',
    'test': [],
    'version': '10.0.1.0.2',
}
