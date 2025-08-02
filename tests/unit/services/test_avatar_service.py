import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
import base64

from services.avatar_service import AvatarService
from models import Account, Membership


@pytest.mark.unit
class TestAvatarService:
    
    def setup_method(self):
        """Set up test data for each test."""
        self.node_id = str(uuid4())
        self.tenant_id = str(uuid4())
        
        # Mock membership
        self.mock_membership = Mock(spec=Membership)
        self.mock_membership.tenant_id = self.tenant_id
        
        # Mock account
        self.mock_account = Mock(spec=Account)
        self.mock_account.memberships = [self.mock_membership]
        
        # Mock S3 service
        self.mock_s3_service = Mock()
        
        # Test image data (base64 encoded small PNG)
        self.test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        self.test_image_bytes = base64.b64decode(self.test_image_b64)
    
    @patch('services.avatar_service.settings')
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_success(self, mock_build_prompt, mock_generate_image, mock_settings):
        """Test successful avatar generation and upload."""
        # Setup mocks
        mock_settings.OPENAI_API_KEY = "test-api-key"
        mock_build_prompt.return_value = "A pixel art portrait of Alex..."
        mock_generate_image.return_value = self.test_image_bytes
        
        expected_s3_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        self.mock_s3_service.upload_file.return_value = expected_s3_url
        
        # Call the method
        result = AvatarService.generate_and_upload(
            node_id=self.node_id,
            name="Alex",
            instructions="Test instructions",
            account=self.mock_account,
            s3_service=self.mock_s3_service
        )
        
        # Assertions
        assert result == expected_s3_url
        mock_build_prompt.assert_called_once_with("Alex", "Test instructions")
        mock_generate_image.assert_called_once_with("A pixel art portrait of Alex...", "test-api-key")
        self.mock_s3_service.upload_file.assert_called_once_with(
            self.test_image_bytes, 
            f"avatars/{self.node_id}.png"
        )
    
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_with_none_values(self, mock_build_prompt, mock_generate_image):
        """Test avatar generation with None name and instructions."""
        mock_build_prompt.return_value = "A pixel art portrait of Alex..."
        mock_generate_image.return_value = self.test_image_bytes
        
        expected_s3_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        self.mock_s3_service.upload_file.return_value = expected_s3_url
        
        result = AvatarService.generate_and_upload(
            node_id=self.node_id,
            name=None,
            instructions=None,
            account=self.mock_account,
            s3_service=self.mock_s3_service
        )
        
        assert result == expected_s3_url
        # Should use defaults for None values
        mock_build_prompt.assert_called_once_with("Alex", "No specific instructions")
    
    def test_generate_and_upload_no_memberships(self):
        """Test avatar generation when account has no memberships."""
        # Mock account with no memberships
        account_no_memberships = Mock(spec=Account)
        account_no_memberships.memberships = []
        
        with pytest.raises(ValueError, match="No tenants available for this user"):
            AvatarService.generate_and_upload(
                node_id=self.node_id,
                name="Alex",
                instructions="Test instructions",
                account=account_no_memberships,
                s3_service=self.mock_s3_service
            )
    
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_s3_upload_fails(self, mock_build_prompt, mock_generate_image):
        """Test avatar generation when S3 upload fails."""
        mock_build_prompt.return_value = "A pixel art portrait of Alex..."
        mock_generate_image.return_value = self.test_image_bytes
        
        # Mock S3 service to return None (upload failure)
        self.mock_s3_service.upload_file.return_value = None
        
        with pytest.raises(RuntimeError, match="Upload to S3 failed"):
            AvatarService.generate_and_upload(
                node_id=self.node_id,
                name="Alex",
                instructions="Test instructions",
                account=self.mock_account,
                s3_service=self.mock_s3_service
            )
    
    @patch('services.avatar_service.random.choice')
    def test_build_prompt_default_values(self, mock_random_choice):
        """Test prompt building with default values."""
        # Setup mock random choices
        mock_random_choice.side_effect = ["woman", "wearing a headset"]
        
        result = AvatarService.build_prompt("DataBot", "Analyzes business data")
        
        expected_prompt = (
            "A pixel art portrait of a woman office worker named DataBot. "
            "This character works as an AI assistant. "
            "Instructions: Analyzes business data. "
            "They are depicted wearing a headset, in a moody and stylish office environment. "
            "Bust shot, dramatic purple and pink lighting, deep shadows, vibrant but not bright. "
            "Rendered in 32-bit retro video game style. No white background, no text in image."
        )
        
        assert result == expected_prompt
        assert mock_random_choice.call_count == 2  # Called for gender and accessory
    
    @patch('services.avatar_service.random.choice')
    def test_build_prompt_randomization(self, mock_random_choice):
        """Test that prompt building uses randomization for variety."""
        # Test different random choices
        mock_random_choice.side_effect = ["man", "with glasses and a serious expression"]
        
        result = AvatarService.build_prompt("CodeHelper", "Assists with programming")
        
        assert "man office worker named CodeHelper" in result
        assert "with glasses and a serious expression" in result
        assert "Instructions: Assists with programming" in result
    
    @patch('services.avatar_service.random.choice')
    def test_build_prompt_all_accessories(self, mock_random_choice):
        """Test that all predefined accessories can be selected."""
        accessories = [
            "wearing a headset",
            "with glasses and a serious expression", 
            "smiling confidently",
            "with a coffee mug",
            "in a blazer and sneakers",
            "leaning slightly, arms crossed"
        ]
        
        for accessory in accessories:
            mock_random_choice.side_effect = ["woman", accessory]
            result = AvatarService.build_prompt("TestBot", "Test instructions")
            assert accessory in result
    
    @patch('services.avatar_service.OpenAI')
    def test_generate_image_success(self, mock_openai_class):
        """Test successful image generation via OpenAI."""
        # Setup mock OpenAI client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response_data = Mock()
        mock_response_data.b64_json = self.test_image_b64
        
        mock_response = Mock()
        mock_response.data = [mock_response_data]
        
        mock_client.images.generate.return_value = mock_response
        
        # Call the method
        result = AvatarService.generate_image("Test prompt", "test-api-key")
        
        # Assertions
        assert result == self.test_image_bytes
        mock_openai_class.assert_called_once_with(api_key="test-api-key")
        mock_client.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt="Test prompt",
            size="1024x1024",
            response_format="b64_json",
            n=1
        )
    
    @patch('services.avatar_service.OpenAI')
    def test_generate_image_openai_error(self, mock_openai_class):
        """Test image generation when OpenAI API raises an error."""
        # Setup mock to raise an exception
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.images.generate.side_effect = Exception("API rate limit exceeded")
        
        # Should let the exception bubble up
        with pytest.raises(Exception, match="API rate limit exceeded"):
            AvatarService.generate_image("Test prompt", "test-api-key")
    
    @patch('services.avatar_service.base64.b64decode')
    @patch('services.avatar_service.OpenAI')
    def test_generate_image_base64_decode_error(self, mock_openai_class, mock_b64decode):
        """Test image generation when base64 decoding fails."""
        # Setup successful OpenAI response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response_data = Mock()
        mock_response_data.b64_json = "invalid-base64"
        
        mock_response = Mock()
        mock_response.data = [mock_response_data]
        mock_client.images.generate.return_value = mock_response
        
        # Setup base64 decode to fail
        mock_b64decode.side_effect = Exception("Invalid base64 string")
        
        with pytest.raises(Exception, match="Invalid base64 string"):
            AvatarService.generate_image("Test prompt", "test-api-key")
    
    @patch('services.avatar_service.settings')
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_uses_settings_api_key(self, mock_build_prompt, mock_generate_image, mock_settings):
        """Test that generate_and_upload uses API key from settings."""
        mock_settings.OPENAI_API_KEY = "settings-api-key"
        mock_build_prompt.return_value = "Test prompt"
        mock_generate_image.return_value = self.test_image_bytes
        
        expected_s3_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        self.mock_s3_service.upload_file.return_value = expected_s3_url
        
        AvatarService.generate_and_upload(
            node_id=self.node_id,
            name="Alex",
            instructions="Test instructions",
            account=self.mock_account,
            s3_service=self.mock_s3_service
        )
        
        mock_generate_image.assert_called_once_with("Test prompt", "settings-api-key")
    
    def test_build_prompt_empty_strings(self):
        """Test prompt building with empty strings."""
        with patch('services.avatar_service.random.choice') as mock_random:
            mock_random.side_effect = ["man", "smiling confidently"]
            
            result = AvatarService.build_prompt("", "")
            
            # Should still include empty name and instructions in prompt
            assert "named . " in result  # Empty name results in "named . "
            assert "Instructions: . " in result  # Empty instructions
    
    @patch('services.avatar_service.settings')
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_empty_strings(self, mock_build_prompt, mock_generate_image, mock_settings):
        """Test avatar generation with empty string inputs."""
        mock_settings.OPENAI_API_KEY = "test-api-key"
        mock_build_prompt.return_value = "Test prompt"
        mock_generate_image.return_value = self.test_image_bytes
        
        expected_s3_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        self.mock_s3_service.upload_file.return_value = expected_s3_url
        
        result = AvatarService.generate_and_upload(
            node_id=self.node_id,
            name="",
            instructions="",
            account=self.mock_account,
            s3_service=self.mock_s3_service
        )
        
        assert result == expected_s3_url
        # Empty strings get converted to defaults via "name or 'Alex'" logic
        mock_build_prompt.assert_called_once_with("Alex", "No specific instructions")
    
    @patch('services.avatar_service.AvatarService.generate_image')
    @patch('services.avatar_service.AvatarService.build_prompt')
    def test_generate_and_upload_whitespace_strings(self, mock_build_prompt, mock_generate_image):
        """Test avatar generation with whitespace-only strings."""
        mock_build_prompt.return_value = "Test prompt"
        mock_generate_image.return_value = self.test_image_bytes
        
        expected_s3_url = f"https://s3.amazonaws.com/bucket/avatars/{self.node_id}.png"
        self.mock_s3_service.upload_file.return_value = expected_s3_url
        
        result = AvatarService.generate_and_upload(
            node_id=self.node_id,
            name="   ",
            instructions="  \t\n  ",
            account=self.mock_account,
            s3_service=self.mock_s3_service
        )
        
        assert result == expected_s3_url
        # Whitespace strings should be passed through as-is
        mock_build_prompt.assert_called_once_with("   ", "  \t\n  ")