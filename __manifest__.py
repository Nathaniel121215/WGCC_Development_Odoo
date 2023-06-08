# -*- coding: utf-8 -*-
{
    'name': "True Move",

    'summary': """
        This module contains the True Move customizations.""",

    'description': """
        Customized module dedicated for True Move requirements that also uses the HRIS system.
    """,

    'author': "WeSupport, Inc.",
    'website': "https://wesupportinc.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','hr_dashboard','hr_recruitment','hr_contract','hr_payroll','sale_timesheet','etsi_dashboard','etsi_dashboard_theme','etsi_hrms','hr_employee_time_clock','etsi_attendance','etsi_hrms_approvers','web_domain_field'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_users.xml',
        'views/res_country.xml',
        'views/hr_domain.xml',
        'views/hr.xml',
        'views/hr_holidays.xml',
        'views/hr_actual_time.xml',
        'views/hr_overtime.xml',
        'views/hr_timesheet.xml',
        'views/backend.xml',
        'views/hr_checkout_form.xml',
        'reports/timesheet_report.xml',
        'reports/timesheet_excel_report.xml',

        # 'views/views.xml',
        # 'views/templates.xml',
    ],
    'qweb': [
            "static/src/xml/hr_dashboard.xml",
            "static/src/xml/attendnce.xml",
        ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'images': [
        # 'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}