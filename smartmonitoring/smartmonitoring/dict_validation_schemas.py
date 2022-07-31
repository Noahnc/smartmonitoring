class ValidationSchemas:
    MANIFEST = {
        'package_version': {
            'required': True,
            'type': 'string'
        },
        'dynamic_secrets': {
            'required': False,
            'nullable': True,
            'type': 'list'
        },
        'containers': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'dict',
                'schema': {
                    'name': {
                        'required': True,
                        'type': 'string'
                    },
                    'hostname': {
                        'required': True,
                        'type': 'string'
                    },
                    'image': {
                        'required': True,
                        'type': 'string'
                    },
                    'privileged': {
                        'required': True,
                        'type': 'boolean'
                    },
                    'files': {
                        'type': 'list',
                        'required': False,
                        'nullable': True,
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'name': {
                                    'required': True,
                                    'type': 'string'
                                },
                                'host_path': {
                                    'required': True,
                                    'type': 'string'
                                },
                                'host_path_dynamic': {
                                    'required': True,
                                    'type': 'boolean'
                                },
                                'container_path': {
                                    'required': True,
                                    'type': 'string'
                                }
                            }
                        }
                    },
                    'ports': {
                        'type': 'list',
                        'required': False,
                        'nullable': True,
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'host_port': {
                                    'required': True,
                                    'type': 'number',
                                    'min': 1,
                                    'max': 65535
                                },
                                'container_port': {
                                    'required': True,
                                    'type': 'number',
                                    'min': 1,
                                    'max': 65535
                                },
                                'protocol': {
                                    'required': True,
                                    'type': 'string',
                                    'allowed': ['tcp', 'udp', ]
                                }
                            }
                        }
                    },
                    'config': {
                        'required': True,
                        'type': 'dict',
                        'schema': {
                            'dynamic': {
                                'type': 'dict',
                                'nullable': True,
                                'required': False
                            },
                            'static': {
                                'type': 'dict',
                                'nullable': True,
                                'required': False
                            },
                            'secrets': {
                                'type': 'dict',
                                'nullable': True,
                                'required': False
                            }
                        }

                    }
                }
            }
        }
    }

    LOCAL_CONFIG = {
        'update_channel': {
            'required': True,
            'type': 'string',
            'allowed': ['STABLE', 'TESTING']
        },
        'debug_logging': {
            'required': True,
            'type': 'boolean'
        },
        'log_file_size_mb': {
            'required': True,
            'type': 'number',
            'min': 10,
            'max': 1000
        },
        'log_file_count': {
            'required': True,
            'type': 'number',
            'min': 1,
            'max': 10
        },
        'update_manifest_url': {
            'required': True,
            'type': 'string'
        },
        'zabbix_proxy_container': {
            'required': True,
            'type': 'dict',
                    'schema': {
                        'proxy_name': {
                            'required': True,
                            'type': 'string'
                        },
                        'psk_key_file': {
                            'required': True,
                            'type': 'string'
                        },
                        'local_settings': {
                            'required': False,
                            'type': 'dict',
                            'nullable': True
                        }

                    }
        },
        'zabbix_mysql_container': {
            'required': False,
            'nullable': True,
            'type': 'dict',
                    'schema': {
                        'local_settings': {
                            'required': False,
                            'type': 'dict',
                            'nullable': True
                        }
                    }
        },
        'zabbix_agent_container': {
            'required': False,
            'nullable': True,
            'type': 'dict',
            'schema': {
                'smartmonitoring_status_file': {
                    'required': True,
                    'type': 'string'
                },
                'local_settings': {
                    'required': False,
                    'type': 'dict',
                    'nullable': True
                }
            }
        }
    }
