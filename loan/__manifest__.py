# -*- coding: utf-8 -*-
{
    'name': "loan",

    'summary': """
        WGCC DEVELOPMENT LOAN
       """,

    'description': """
       WGCC DEVELOPMENT LOAN
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/loan_amortization_form.xml',
        'views/menu.xml',
        'views/loan_application.xml',
    ],
}