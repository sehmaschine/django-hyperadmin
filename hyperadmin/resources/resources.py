from django import http
from django import forms
from django.conf.urls.defaults import patterns, url

from hyperadmin.hyperobjects import Link, ResourceItem


class EmptyForm(forms.Form):
    def __init__(self, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(EmptyForm, self).__init__(**kwargs)

class BaseResource(object):
    resource_class = '' #hint to the client how this resource is used
    resource_item_class = ResourceItem
    form_class = EmptyForm
    
    def __init__(self, resource_adaptor, site, parent_resource=None):
        self.resource_adaptor = resource_adaptor
        self.site = site
        self.parent = parent_resource
    
    def get_app_name(self):
        raise NotImplementedError
    app_name = property(get_app_name)
    
    def get_urls(self):
        urlpatterns = self.get_extra_urls()
        return urlpatterns
    
    def get_extra_urls(self):
        return patterns('',)
    
    def urls(self):
        return self.get_urls(), self.app_name, None
    urls = property(urls)
    
    def reverse(self, name, *args, **kwargs):
        return self.site.reverse(name, *args, **kwargs)
    
    def as_view(self, view, cacheable=False):
        return self.site.as_view(view, cacheable)
    
    def as_nonauthenticated_view(self, view, cacheable=False):
        return self.site.as_nonauthenticated_view(view, cacheable)
    
    def get_view_kwargs(self):
        return {'resource':self,
                'resource_site':self.site,}
    
    def get_embedded_links(self, instance=None):
        return []
    
    def get_outbound_links(self, instance=None):
        return []
    
    def get_templated_queries(self):
        return []
    
    #TODO find a better name
    def get_ln_links(self, instance=None):
        return []
    
    #TODO find a better name
    def get_li_links(self, instance=None):
        return []
    
    def get_instance_url(self, instance):
        return None
    
    def get_form_class(self, instance=None):
        return self.form_class
    
    def get_form_kwargs(self, **kwargs):
        return kwargs
    
    def generate_response(self, media_type, content_type, link=None, meta=None):
        return media_type.serialize(content_type=content_type, link=link, meta=meta)
    
    def get_related_resource_from_field(self, field):
        return self.site.get_related_resource_from_field(field)
    
    def get_html_type_from_field(self, field):
        return self.site.get_html_type_from_field(field)
    
    def get_child_resource_links(self):
        return []
    
    def get_absolute_url(self):
        raise NotImplementedError
    
    def get_resource_item(self, instance):
        return self.resource_item_class(resource=self, instance=instance)
    
    def get_prompt(self, instance):
        return unicode(instance)
    
    def get_resource_link_item(self, filter_params=None):
        return None
    
    def get_resource_link(self, **kwargs):
        link_kwargs = {'url':self.get_absolute_url(),
                       'resource':self,
                       'resource_item':self.get_resource_link_item(),
                       'rel':'self',
                       'prompt':self.prompt(),}
        link_kwargs.update(kwargs)
        resource_link = Link(**link_kwargs)
        return resource_link
    
    def get_breadcrumb(self):
        return self.get_resource_link(rel='breadcrumb')
    
    def get_breadcrumbs(self):
        breadcrumbs = []
        if self.parent:
            breadcrumbs = self.parent.get_breadcrumbs()
        breadcrumbs.append(self.get_breadcrumb())
        return breadcrumbs
    
    def prompt(self):
        return unicode(self)

class CRUDResource(BaseResource):
    resource_class = 'crudresource'
    
    #TODO support the following:
    actions = []
    
    list_view = None
    add_view = None
    detail_view = None
    delete_view = None
    form_class = None
    
    def get_resource_name(self):
        raise NotImplementedError
    resource_name = property(get_resource_name)
    
    def prompt(self):
        return self.resource_name
    
    def get_urls(self):
        def wrap(view, cacheable=False):
            return self.as_view(view, cacheable)
        
        init = self.get_view_kwargs()
        
        # Admin-site-wide views.
        urlpatterns = self.get_extra_urls()
        urlpatterns += patterns('',
            url(r'^$',
                wrap(self.list_view.as_view(**init)),
                name='%s_%s_list' % (self.app_name, self.resource_name)),
            url(r'^add/$',
                wrap(self.add_view.as_view(**init)),
                name='%s_%s_add' % (self.app_name, self.resource_name)),
            url(r'^(?P<pk>\w+)/$',
                wrap(self.detail_view.as_view(**init)),
                name='%s_%s_detail' % (self.app_name, self.resource_name)),
            url(r'^(?P<pk>\w+)/delete/$',
                wrap(self.delete_view.as_view(**init)),
                name='%s_%s_delete' % (self.app_name, self.resource_name)),
        )
        return urlpatterns
    
    def get_add_url(self):
        return self.reverse('%s_%s_add' % (self.app_name, self.resource_name))
    
    def get_instance_url(self, instance):
        return self.reverse('%s_%s_detail' % (self.app_name, self.resource_name), pk=instance.pk)
    
    def get_delete_url(self, instance):
        return self.reverse('%s_%s_delete' % (self.app_name, self.resource_name), pk=instance.pk)
    
    def get_absolute_url(self):
        return self.reverse('%s_%s_list' % (self.app_name, self.resource_name))
    
    def get_item_link(self, instance):
        resource_item = self.get_resource_item(instance)
        item_link = Link(url=resource_item.get_absolute_url(),
                         resource=self,
                         resource_item=resource_item,
                         rel='item',
                         prompt=self.get_prompt(instance),)
        return item_link
    
    def get_create_link(self, form_kwargs, form_class=None, form=None):
        if form_class is None:
            form_class = self.get_form_class()
        create_link = Link(url=self.get_add_url(),
                           resource=self,
                           on_submit=self.handle_create_submission,
                           method='POST',
                           form=form,
                           form_class=form_class,
                           form_kwargs=form_kwargs,
                           prompt='create',
                           rel='create',)
        return create_link
    
    def get_update_link(self, form_kwargs, form_class=None, form=None):
        if form_class is None:
            form_class = self.get_form_class()
        update_link = Link(url=self.get_instance_url(form_kwargs['instance']),
                           resource=self,
                           on_submit=self.handle_update_submission,
                           resource_item=self.get_resource_item(form_kwargs['instance']),
                           method='POST',
                           form=form,
                           form_class=form_class,
                           form_kwargs=form_kwargs,
                           prompt='update',
                           rel='update',)
        return update_link
    
    def get_delete_link(self, form_kwargs, form_class=None):
        delete_link = Link(url=self.get_delete_url(form_kwargs['instance']),
                           resource=self,
                           resource_item=self.get_resource_item(form_kwargs['instance']),
                           on_submit=self.handle_delete_submission,
                           rel='delete',
                           prompt='delete',
                           method='POST')
        return delete_link
    
    def handle_create_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            return self.get_item_link(instance=instance)
        return self.get_create_link(form_kwargs=link.form_kwargs, form=form)
    
    def handle_update_submission(self, link, submit_kwargs):
        form = link.get_form(**submit_kwargs)
        if form.is_valid():
            instance = form.save()
            return self.get_item_link(instance=instance)
        return self.get_update_link(form_kwargs=link.form_kwargs, form=form)
    
    def handle_delete_submission(self, link, submit_kwargs):
        instance = link.resource_item.instance
        instance.delete()
        return self.get_resource_link()
    
    def has_add_permission(self, user):
        return True
    
    def has_change_permission(self, user, obj=None):
        return True
    
    def has_delete_permission(self, user, obj=None):
        return True
    
    def get_embedded_links(self, instance=None):
        if instance:
            delete_link = self.get_delete_link(form_kwargs={'instance':instance})
            return [delete_link]
        add_link = self.get_create_link({})
        return [add_link]
    
    def get_outbound_links(self, instance=None):
        if instance:
            return []
        else:
            return self.get_breadcrumbs()
    
    def get_templated_queries(self):
        #search and filter goes here
        return []
    
    def get_actions(self, request):
        actions = self.site.get_actions(request)
        for func in self.actions:
            if isinstance(func, basestring):
                #TODO register as new func in urls, create link for it
                func = getattr(self, func)
            assert callable(func)
            name = func.__name__
            description = getattr(func, 'short_description', name.replace('_', ' '))
            #sorteddictionary
            actions[name] = (func, name, description)
        return actions
    
    def get_action(self, request, action):
        actions = self.get_actions(request)
        return actions[action]
    
    def __unicode__(self):
        return u'CRUD Resource: %s/%s' % (self.app_name, self.resource_name)

