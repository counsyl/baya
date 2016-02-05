def permission_context(request):
    func = request.resolver_match.func
    gate = getattr(func, '_gate', None)
    data = {}
    if gate:
        data = {
            'baya_permissions': gate,
            'baya_membership': gate.get_membership_node(request),
        }

    if hasattr(request, 'baya_permission_denied'):
        data['baya_permission_denied'] = request.baya_permission_denied
    return data
