def language_processor(request):
    # Django's LocaleMiddleware sets request.LANGUAGE_CODE
    lang = getattr(request, 'LANGUAGE_CODE', 'ru')
    lang = 'ky' if lang == 'ky' else 'ru'
    return {'current_lang': lang}


def theme_processor(request):
    theme = request.session.get('site_theme', 'dark')
    return {'site_theme': theme}
