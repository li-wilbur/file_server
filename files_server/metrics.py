from prometheus_client import Counter, Histogram

# HTTP请求指标
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 文件操作指标
FILE_OPERATIONS = Counter(
    'file_operations_total',
    'Total file operations',
    ['operation', 'status']
)

FILE_SIZE = Histogram(
    'file_size_bytes',
    'File size in bytes',
    ['operation']
) 