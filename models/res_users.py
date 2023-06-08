from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def default_get(self, fields):
        result = super(ResUsers, self).default_get(fields)
        result['tz'] = 'Asia/Bangkok'
        return result


