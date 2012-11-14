'''
These are objects generated by the resource and are serialized by a media type.
'''
from copy import copy

from django.http import QueryDict


class Link(object):
    """
    Represents an available action or state transition.
    """
    def __init__(self, url, resource, method='GET', form=None, form_class=None, form_kwargs=None, link_factor=None, include_form_params_in_url=False,
                 descriptors=None, prompt=None, cu_headers=None, cr_headers=None, on_submit=None, **cl_headers):
        self._url = url
        self._method = str(method).upper() #CM
        self.state = resource.state.get('endpoint_state', resource.state) #TODO endpoint state would be better
        self._form = form
        self.form_class = form_class
        self.form_kwargs = form_kwargs
        self.link_factor = link_factor
        self.include_form_params_in_url = include_form_params_in_url
        self.descriptors = descriptors #is this needed?
        self.cl_headers = cl_headers
        self.prompt = prompt
        self.cu_headers = cu_headers
        self.cr_headers = cr_headers
        self.on_submit = on_submit
    
    @property
    def resource(self):
        return self.state.resource
    
    @property
    def rel(self):
        return self.cl_headers.get('rel', None)
    
    @property
    def classes(self):
        if not 'classes' in self.cl_headers:
            if 'class' in self.cl_headers:
                self.cl_headers['classes'] = self.cl_headers['class'].split()
            else:
                self.cl_headers['classes'] = []
        return self.cl_headers['classes']
    
    def get_base_url(self):
        #include_form_params_in_url=False
        if self.get_link_factor() == 'LT' and self.include_form_params_in_url: #TODO absorb this in link._url
            if '?' in self._url:
                base_url, url_params = self._url.split('?', 1)
            else:
                base_url, url_params = self._url, ''
            params = QueryDict(url_params, mutable=True)
            form = self.get_form()
            #extract get params
            for field in form:
                val = field.value()
                if val is not None:
                    params[field.html_name] = val
            return '%s?%s' % (base_url, params.urlencode())
        return self._url
    
    def clone_into_links(self):
        assert self.get_link_factor() == 'LT'
        links = list()
        #TODO find a better way
        form = self.get_form()
        options = [(field, key) for key, field in form.fields.iteritems() if hasattr(field, 'choices')]
        for option_field, key in options:
            for val, label in option_field.choices:
                if not val:
                    continue
                form_kwargs = copy(self.form_kwargs)
                form_kwargs['initial'] = {key: val}
                option = self.clone(prompt=label, form_kwargs=form_kwargs, include_form_params_in_url=True)
                links.append(option)
        return links
    
    def get_absolute_url(self):
        """
        The url for this link
        """
        return self.state.get_link_url(self)
    
    def get_link_factor(self):
        """
        Returns a two character representation of the link factor.
        
        * LI - Idempotent
        * LN - Non-Idempotent
        * LT - Templated link
        * LO - Outbound link
        * LI - Embedded link
        """
        if self.link_factor:
            return self.link_factor
        if self._method in ('PUT', 'DELETE'):
            return 'LI'
        if self._method == 'POST':
            return 'LN'
        if self._method == 'GET':
            if self.form_class:
                return 'LT'
            #TODO how do we determine which to return?
            return 'LO' #link out to this content
            return 'LE' #embed this content
        return 'L?'
    
    @property
    def is_simple_link(self):
        """
        Returns True if this link is simply to be followed
        """
        if self.get_link_factor() in ('LO', 'LE'):
            return True
        return False
    
    @property
    def method(self):
        """
        The HTTP method of the link
        """
        if self.is_simple_link:
            return 'GET'
        return self._method
    
    def class_attr(self):
        return u' '.join(self.classes)
    
    def get_form_kwargs(self, **form_kwargs):
        if self.form_kwargs:
            kwargs = copy(self.form_kwargs)
        else:
            kwargs = dict()
        kwargs.update(form_kwargs)
        return kwargs
    
    def get_form(self, **form_kwargs):
        kwargs = self.get_form_kwargs(**form_kwargs)
        form = self.form_class(**kwargs)
        return form
    
    @property
    def form(self):
        """
        Returns the active form for the link. Returns None if there is no form.
        """
        if self._form is None and self.form_class and not self.is_simple_link:
            self._form = self.get_form()
        return self._form
    
    @property
    def errors(self):
        """
        Returns the validation errors belonging to the form
        """
        if self.is_simple_link:
            return None
        if self.form_class:
            return self.form.errors
        return None
    
    def submit(self, **kwargs):
        '''
        Returns a link representing the result of the action taken.
        The resource_item of the link may represent the updated/created object
        or in the case of a collection resource item you get access to the filter items
        '''
        on_submit = self.on_submit
        
        if on_submit is None:
            pass #TODO follow link
        
        return on_submit(link=self, submit_kwargs=kwargs)
    
    def clone(self, **kwargs):
        a_clone = copy(self)
        a_clone._form = kwargs.pop('form', self._form)
        for key, value in kwargs.iteritems():
            setattr(a_clone, key, value)
        return a_clone


class Namespace(object):
    """
    Represents data that is associated to our current state. Typically is an association with another resource.
    """
    def __init__(self, name, link, state):
        self.name = name
        self.link = link
        self.state = state.copy()
    
    def get_namespaces(self):
        return dict()
    
    def get_prompt(self):
        return self.state.resource.get_prompt()

class ResourceItem(object):
    '''
    Represents an instance that is bound to a resource
    '''
    form_class = None
    
    def __init__(self, resource, instance):
        self.state = resource.state.get('endpoint_state', resource.state)
        self.instance = instance
    
    @property
    def resource(self):
        return self.state.resource
    
    def get_embedded_links(self):
        return self.state.get_item_embedded_links(self)
    
    def get_outbound_links(self):
        return self.state.get_item_outbound_links(self)
    
    def get_templated_queries(self):
        return self.state.get_item_templated_queries(self)
    
    def get_ln_links(self):
        return self.state.get_item_ln_links(self)
    
    def get_idempotent_links(self):
        return self.state.get_item_idempotent_links(self)
    
    def get_item_link(self):
        return self.state.get_item_link(self)
    
    def get_absolute_url(self):
        return self.resource.get_item_url(self)
    
    def get_form_class(self):
        if self.form_class is not None:
            return self.form_class
        return self.resource.get_form_class()
    
    def get_form_kwargs(self, **kwargs):
        kwargs = self.resource.get_form_kwargs(**kwargs)
        kwargs['instance'] = self.instance
        return kwargs
    
    def get_form(self, **form_kwargs):
        form_cls = self.get_form_class()
        kwargs = self.get_form_kwargs(**form_kwargs)
        form = form_cls(**kwargs)
        return form
    
    @property
    def form(self):
        """
        Mediatype uses this form to serialize the result
        """
        if not hasattr(self, '_form'):
            self._form = self.get_form()
        return self._form
    
    def get_prompt(self):
        """
        Returns a string representing the item
        """
        return self.resource.get_item_prompt(self)
    
    def get_resource_items(self):
        return [self]
    
    def get_namespaces(self):
        """
        Returns namespaces associated with this item
        """
        return self.resource.get_item_namespaces(self)

