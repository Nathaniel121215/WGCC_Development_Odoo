from odoo import api, fields, models, _

class TrueMoveHRDomain(models.Model):
    _name = 'hr.domain'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', track_visibility='onchange')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The Domain Name already exist!')
    ]

    active = fields.Boolean(string="Active", default=True, track_visibility='onchange')
    department_manager_id = fields.Many2one('hr.employee', string="Department Manager", domain=lambda self: ['|',('user_id.groups_id', '=', self.env.ref('hr.group_hr_manager').id),('user_id.groups_id', '=', self.env.ref('hr.group_hr_user').id)], track_visibility='onchange')
    department_manager_user_id = fields.Many2one('res.users', string="Department Manager User", domain=lambda self: ['|',('groups_id', '=', self.env.ref('hr.group_hr_manager').id),('groups_id', '=', self.env.ref('hr.group_hr_user').id)])
    admin_user = fields.Many2one('res.users', string="Admin User", compute='_compute_admin_user', store=True)
    
    @api.onchange('department_manager_id')
    def onchange_department_manager_id(self):
        for record in self:
            record.department_manager_user_id = False
            if record.department_manager_id:
                record.department_manager_user_id = record.department_manager_id.user_id.id
                
    @api.depends('name','active','department_manager_id','department_manager_user_id')
    def _compute_admin_user(self):
        self.admin_user = self.env['res.users'].search([('name','ilike','admin')], limit=1).id
        
    @api.multi
    def toggle_active(self):
        if not self.active:
            self.active = True
        else:
            self.active = False