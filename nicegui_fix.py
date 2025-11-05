"""
NiceGUI 兼容性修复
解决 TemplateResponse request 参数错误

这个错误通常是由于 Starlette 0.27+ 版本中 TemplateResponse 不再接受 request 参数导致的。
最简单的解决方案是降级 Starlette 或升级 NiceGUI。
"""
import warnings

# 尝试修复兼容性问题
try:
    from starlette.templating import Jinja2Templates
    import inspect
    
    # 检查 TemplateResponse 的签名
    sig = inspect.signature(Jinja2Templates.TemplateResponse)
    
    # 如果签名中不包含 request 参数，可能需要应用补丁
    if 'request' not in str(sig):
        # NiceGUI 可能在内部使用了旧版本的 API
        # 这里提供一个兼容性包装
        _original_template_response = Jinja2Templates.TemplateResponse
        
        def _patched_template_response(self, name: str, context: dict = None, status_code: int = 200, 
                                       headers: dict = None, media_type: str = None, **kwargs):
            """修复后的 TemplateResponse"""
            # 移除 kwargs 中的 request（如果存在）
            kwargs.pop('request', None)
            
            # 确保 context 是字典
            if context is None:
                context = {}
            
            # 调用原始方法
            return _original_template_response(self, name, context, status_code=status_code, 
                                              headers=headers, media_type=media_type, **kwargs)
        
        # 应用补丁
        Jinja2Templates.TemplateResponse = _patched_template_response
        warnings.warn("已应用 NiceGUI 兼容性修复，建议升级 NiceGUI 到最新版本")
        
except Exception as e:
    warnings.warn(f"无法应用兼容性修复: {e}，建议升级 NiceGUI 或降级 Starlette")

