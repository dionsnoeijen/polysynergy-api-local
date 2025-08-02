import pytest
from unittest.mock import Mock, patch

from services.gather_nodes_service import discover_nodes


@pytest.mark.unit
class TestGatherNodesService:
    
    def setup_method(self):
        """Reset the global cache before each test."""
        import services.gather_nodes_service
        services.gather_nodes_service._DISCOVERED_NODES = None
    
    def test_discover_nodes_caching_behavior(self):
        """Test that results are cached after first call."""
        with patch('services.gather_nodes_service.import_module') as mock_import:
            mock_import.side_effect = ImportError("No package")
            
            # First call
            result1 = discover_nodes(["test_package"])
            
            # Second call should return cached empty result without calling import_module again
            result2 = discover_nodes(["test_package"])
            
            assert result1 == result2 == []
            # import_module should only be called once due to caching
            assert mock_import.call_count == 1
    
    @patch('services.gather_nodes_service.import_module')
    def test_discover_nodes_package_import_failure(self, mock_import_module):
        """Test node discovery when package import fails."""
        mock_import_module.side_effect = ImportError("No module named 'polysynergy_nodes'")
        
        result = discover_nodes(["polysynergy_nodes"])
        
        assert result == []
        mock_import_module.assert_called_with("polysynergy_nodes")
    
    def test_discover_nodes_default_packages(self):
        """Test that default packages are used when none specified."""
        with patch('services.gather_nodes_service.import_module') as mock_import:
            mock_import.side_effect = ImportError("No package")
            
            result = discover_nodes()  # No packages specified
            
            # Should attempt to import default package
            mock_import.assert_called_with("polysynergy_nodes")
            assert result == []
    
    @patch('services.gather_nodes_service.import_module')
    def test_discover_nodes_multiple_packages_partial_failure(self, mock_import_module):
        """Test node discovery with some packages failing to import."""
        def import_side_effect(package_name):
            if package_name == "failing_package":
                raise ImportError("Package failed")
            elif package_name == "working_package":
                mock_pkg = Mock()
                mock_pkg.__file__ = "/path/to/working_package/__init__.py"
                return mock_pkg
            else:
                raise ImportError("Unknown package")
        
        mock_import_module.side_effect = import_side_effect
        
        # Mock Path to return empty glob results for working package
        with patch('services.gather_nodes_service.Path') as mock_path_class:
            mock_path = Mock()
            mock_path.parent.glob.return_value = []  # No Python files found
            mock_path_class.return_value = mock_path
            
            result = discover_nodes(["failing_package", "working_package"])
            
            assert result == []  # No nodes found even though one package imported successfully
            
            # Verify both packages were attempted
            assert mock_import_module.call_count == 2
            mock_import_module.assert_any_call("failing_package")
            mock_import_module.assert_any_call("working_package")
    
    @patch('services.gather_nodes_service.import_module')
    def test_discover_nodes_empty_packages_list(self, mock_import_module):
        """Test node discovery with empty packages list uses defaults."""
        mock_import_module.side_effect = ImportError("No package")
        
        result = discover_nodes([])
        
        # Should still use default packages
        assert result == []
        mock_import_module.assert_called_with("polysynergy_nodes")
    
    def test_discover_nodes_global_cache_persistence(self):
        """Test that the global cache persists across different calls."""
        import services.gather_nodes_service
        
        # Manually set cache
        test_nodes = [{"id": "cached_node", "name": "Cached Node"}]
        services.gather_nodes_service._DISCOVERED_NODES = test_nodes
        
        # Any call should return cached result without attempting imports
        with patch('services.gather_nodes_service.import_module') as mock_import:
            result = discover_nodes(["any_package"])
            
            assert result == test_nodes
            # No imports should happen due to cache
            mock_import.assert_not_called()
    
    def test_discover_nodes_none_packages_parameter(self):
        """Test that None packages parameter uses default packages."""
        with patch('services.gather_nodes_service.import_module') as mock_import:
            mock_import.side_effect = ImportError("No package")
            
            result = discover_nodes(None)
            
            # Should use default packages when None is passed
            assert result == []
            mock_import.assert_called_with("polysynergy_nodes")
    
    @patch('services.gather_nodes_service.import_module')
    def test_discover_nodes_handles_package_without_file_attribute(self, mock_import_module):
        """Test handling of packages that don't have __file__ attribute."""
        mock_package = Mock()
        del mock_package.__file__  # Remove __file__ attribute
        mock_import_module.return_value = mock_package
        
        result = discover_nodes(["test_package"])
        
        # Should handle gracefully and return empty result
        assert result == []
    
    @patch('services.gather_nodes_service.import_module')  
    def test_discover_nodes_exception_handling_in_main_loop(self, mock_import_module):
        """Test that exceptions in the main discovery loop are handled."""
        # Mock package import to succeed but cause an exception during processing
        mock_package = Mock()
        mock_package.__file__ = "/path/to/package/__init__.py"
        mock_import_module.return_value = mock_package
        
        # Mock Path to raise an exception
        with patch('services.gather_nodes_service.Path') as mock_path:
            mock_path.side_effect = Exception("Path processing failed")
            
            # Should not raise exception, just return empty result
            result = discover_nodes(["test_package"])
            
            assert result == []