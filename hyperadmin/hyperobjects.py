class Link(object):
    def __init__(self, url, method='GET', form=None, classes=[], descriptors=None, rel=None, prompt=None, cu_headers=None, cr_headers=None, response=None):
        '''
        fields = dictionary of django fields describing the accepted data
        descriptors = dictionary of data describing the link
        
        '''
        self.url = url
        self.method = str(method).upper() #CM
        self.form = form
        self.classes = classes
        self.descriptors = descriptors
        self.rel = rel #CL
        self.prompt = prompt
        self.cu_headers = cu_headers
        self.cr_headers = cr_headers
        self.response = response
    
    def get_link_factor(self):
        if self.method in ('PUT', 'DELETE'):
            return 'LI'
        if self.method == 'POST':
            return 'LN'
        if self.method == 'GET':
            if self.form:
                return 'LT'
            #TODO how do we determine which to return?
            return 'LO'
            return 'LE'
        return 'L?'
    
    def class_attr(self):
        return u' '.join(self.classes)
    
    def submit(self, media_type=None, content_type=None, meta=None):
        assert self.response
        if self.form:
            assert self.form.is_valid()
        if media_type is None:
            media_type = lambda **kwargs: kwargs
        if content_type is None:
            content_type = 'text/html'
        return self.response(media_type=media_type, content_type=content_type, meta=meta, form_link=self)

class ResourceItem(object):
    form_class = None
    
    def __init__(self, resource, instance):
        self.resource = resource
        self.instance = instance
    
    def get_embedded_links(self):
        return self.resource.get_embedded_links(instance=self.instance)
    
    def get_outbound_links(self):
        return self.resource.get_outbound_links(instance=self.instance)
    
    def get_templated_queries(self):
        return self.resource.get_templated_queries(instance=self.instance)
    
    def get_ln_links(self):
        return self.resource.get_ln_links(instance=self.instance)
    
    def get_li_links(self):
        return self.resource.get_li_links(instance=self.instance)
    
    def get_absolute_url(self):
        return self.resource.get_instance_url(instance=self.instance)
    
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
    
    def get_prompt(self):
        return self.resource.get_prompt(self.instance)

