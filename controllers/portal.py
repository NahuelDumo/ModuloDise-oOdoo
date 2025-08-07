# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class DesignPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'design_count' in counters:
            domain = self._get_designs_domain()
            values['design_count'] = request.env['design.design'].search_count(domain)
        return values
    
    def _get_designs_domain(self):
        partner = request.env.user.partner_id
        return [
            ('cliente_id', 'child_of', partner.commercial_partner_id.ids),
            ('state', 'in', ['cliente', 'correcciones_solicitadas'])
        ]
    
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values['design_count'] = request.env['design.design'].search_count(self._get_designs_domain())
        return values
    
    @route(['/my/designs', '/my/designs/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_designs(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Design = request.env['design.design']
        domain = self._get_designs_domain()
        
        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'create_date desc'},
            'name': {'label': _('Nombre'), 'order': 'name'},
        }
        
        # Default sort by date
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Pager
        design_count = Design.search_count(domain)
        pager = portal_pager(
            url="/my/designs",
            url_args={'sortby': sortby},
            total=design_count,
            page=page,
            step=self._items_per_page
        )
        
        designs = Design.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'designs': designs,
            'page_name': 'design',
            'default_url': '/my/designs',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("ModuloDisenoOdoo.portal_my_designs", values)
    
    @route(['/my/design/<int:design_id>'], type='http', auth="user", website=True)
    def portal_my_design(self, design_id, **kw):
        try:
            design_sudo = self._document_check_access('design.design', design_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        values = self._prepare_portal_layout_values()
        values.update({
            'design': design_sudo,
            'page_name': 'design',
        })
        return request.render("ModuloDisenoOdoo.portal_my_design", values)
    
    @route(['/my/design/approve'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Aprobar el diseño
        design_sudo.sudo().action_aprobado_por_cliente()
        
        # Redirigir con mensaje de éxito
        return request.redirect("/my/designs?message=design_approved")
    
    @route(['/my/design/approve-with-changes'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_with_changes_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Aprobar con correcciones
        design_sudo.sudo().action_aprobado_con_correcciones(message)
        
        # Redirigir con mensaje de éxito
        return request.redirect("/my/designs?message=design_approved_with_changes")
    
    @route(['/my/design/reject'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def reject_design(self, design_id, message='', **post):
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if design_sudo.cliente_id not in partner | partner.commercial_partner_id:
            return request.redirect('/my')
            
        # Rechazar el diseño
        design_sudo.sudo().action_rechazado_por_cliente(message)
        
        # Redirigir con mensaje de éxito
        return request.redirect("/my/designs?message=design_rejected")
