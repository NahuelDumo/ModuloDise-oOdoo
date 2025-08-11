# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import logging

# Configurar el nivel de logging para este módulo
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

class DesignPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'design_count' in counters:
            domain = self._get_designs_domain()
            values['design_count'] = request.env['design.design'].search_count(domain)
            _logger.debug(f"[PORTAL] Design count calculado: {values['design_count']}")
        return values
    
    def _get_designs_domain(self):
        """Dominio base para buscar diseños visibles para el usuario actual.
        Coincide con la regla de seguridad design_design_rule_cliente."""
        partner = request.env.user.partner_id
        _logger.debug(f"[PORTAL] Usuario: {request.env.user.name} (ID: {request.env.user.id})")
        _logger.debug(f"[PORTAL] Partner: {partner.name} (ID: {partner.id})")
        _logger.debug(f"[PORTAL] Partner Comercial: {partner.commercial_partner_id.name} (ID: {partner.commercial_partner_id.id})")
        
        # Verificar si el partner tiene algún diseño asociado directamente
        designs_direct = request.env['design.design'].search([('cliente_id', '=', partner.id)])
        _logger.debug(f"[PORTAL] Diseños asociados directamente al partner: {len(designs_direct)}")
        for idx, design in enumerate(designs_direct, 1):
            _logger.debug(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Verificar diseños en la jerarquía del partner comercial
        designs_hierarchy = request.env['design.design'].search([('cliente_id', 'child_of', partner.commercial_partner_id.id)])
        _logger.debug(f"[PORTAL] Diseños en la jerarquía del partner comercial: {len(designs_hierarchy)}")
        for idx, design in enumerate(designs_hierarchy, 1):
            _logger.debug(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Dominio final con todos los filtros
        domain = [
            ('cliente_id', 'child_of', partner.commercial_partner_id.id),
            ('visible_para_cliente', '=', True),
            ('state', 'in', ['cliente', 'correcciones_solicitadas', 'aprobado', 'rechazado', 'esperando_cliente'])
        ]
        
        _logger.debug(f"[PORTAL] Dominio de búsqueda: {domain}")
        
        # Verificar cuántos diseños coinciden con el dominio completo
        matching_designs = request.env['design.design'].search(domain)
        _logger.debug(f"[PORTAL] Diseños que coinciden con el dominio: {len(matching_designs)}")
        for idx, design in enumerate(matching_designs, 1):
            _logger.debug(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}, Visible: {design.visible_para_cliente}")
        
        return domain
    
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        domain = self._get_designs_domain()
        design_count = request.env['design.design'].search_count(domain)
        values['design_count'] = design_count
        _logger.info(f"Portal layout - design_count: {design_count}")
        return values
    
    @route(['/my/designs', '/my/designs/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_designs(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        _logger.info("=== INICIO DE PORTAL_MY_DESIGNS ===")
        
        # Obtener información del usuario actual
        partner = request.env.user.partner_id
        _logger.info(f"Usuario: {request.env.user.name}")
        _logger.info(f"Partner ID: {partner.id}")
        _logger.info(f"Partner Comercial ID: {partner.commercial_partner_id.id}")
        
        # Obtener el dominio de búsqueda (ya incluye filtros de seguridad)
        domain = self._get_designs_domain()
        Design = request.env['design.design']
        
        # Buscar diseños respetando las reglas de seguridad (sin sudo)
        designs = Design.search(domain, order='create_date desc')
        _logger.info(f"[PORTAL] Diseños encontrados para {request.env.user.name}: {len(designs)}")
        
        # Solo para depuración en logs - no afecta la lógica
        if _logger.isEnabledFor(logging.DEBUG):
            for design in designs:
                _logger.debug(f"  - ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        values = self._prepare_portal_layout_values()
        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'create_date desc'},
            'name': {'label': _('Nombre'), 'order': 'name'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filtros de fecha si se proporcionan
        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<=', date_end)]
            designs = Design.search(domain)
        
        # Pager
        design_count = len(designs)
        pager = portal_pager(
            url="/my/designs",
            url_args={'sortby': sortby, 'date_begin': date_begin, 'date_end': date_end},
            total=design_count,
            page=page,
            step=self._items_per_page
        )
        
        # Aplicar ordenamiento y paginación
        designs = designs.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        values.update({
            'designs': designs,
            'page_name': 'design',
            'default_url': '/my/designs',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'date_begin': date_begin,
            'date_end': date_end,
        })
        
        _logger.info("=== FIN DE PORTAL_MY_DESIGNS ===")
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
        if hasattr(design_sudo, 'action_aprobado_por_cliente'):
            design_sudo.sudo().action_aprobado_por_cliente()
        else:
            # Fallback manual si no existe el método
            design_sudo.sudo().write({
                'state': 'aprobado',
                'fecha_aprobacion_cliente': request.env.cr.now(),
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_approved")
    
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
        if hasattr(design_sudo, 'action_aprobado_con_correcciones'):
            design_sudo.sudo().action_aprobado_con_correcciones(message)
        else:
            # Fallback manual
            design_sudo.sudo().write({
                'state': 'correcciones_solicitadas',
                'mensaje_cliente': message,
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_approved_with_changes")
    
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
        if hasattr(design_sudo, 'action_rechazado_por_cliente'):
            design_sudo.sudo().action_rechazado_por_cliente(message)
        else:
            # Fallback manual
            design_sudo.sudo().write({
                'state': 'rechazado',
                'mensaje_cliente': message,
            })
        
        # Redirigir con mensaje de éxito
        return request.redirect(f"/my/design/{design_id}?message=design_rejected")
    
    def _document_check_access(self, model_name, document_id, access_token=None):
        """Verificar acceso a un documento de manera segura para usuarios del portal"""
        try:
            # Obtener el registro con el usuario actual
            document = request.env[model_name].browse(document_id)
            
            # Verificar que el documento existe
            if not document.exists():
                _logger.warning(f"Documento {model_name} ID {document_id} no encontrado")
                raise MissingError(_("El documento no existe o fue eliminado"))
                
            # Verificar que el usuario sea el cliente asignado al diseño
            if document.cliente_id.id != request.env.user.partner_id.id:
                _logger.warning(
                    f"Acceso denegado: Usuario {request.env.user.id} intentó acceder "
                    f"al diseño {document_id} que pertenece al cliente {document.cliente_id.id}"
                )
                raise AccessError(_("No tiene permiso para acceder a este diseño"))
                
            # Verificar permisos básicos de lectura
            try:
                document.check_access_rights('read')
                document.check_access_rule('read')
            except AccessError as e:
                _logger.warning(f"Error de permisos en documento {document_id}: {str(e)}")
                raise AccessError(_("No tiene permiso para ver este documento"))
                
            return document
            
        except Exception as e:
            _logger.error(f"Error en _document_check_access: {str(e)}", exc_info=True)
            raise