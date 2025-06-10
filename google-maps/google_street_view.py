import time
import requests
import urllib.parse
from typing import Any

from griptape.artifacts import ImageUrlArtifact
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode, ParameterGroup
from griptape_nodes.exe_types.node_types import AsyncResult, ControlNode
from griptape_nodes.traits.options import Options
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes, logger

SERVICE = "Google_Maps"
API_KEY_ENV_VAR = "GOOGLE_MAPS_API_KEY"
BASE_URL = "https://maps.googleapis.com/maps/api/streetview"


class GoogleStreetView(ControlNode):
    """
    Google Street View Node that fetches street view images from Google's Street View Static API.
    
    Takes an address or coordinates as input and outputs an ImageUrlArtifact containing
    the street view image. The image is also displayed on the node interface.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.category = "Maps/Google"
        self.description = "Fetch Street View image from Google Street View Static API"

        # Location Group
        with ParameterGroup(name="Location") as location_group:
            Parameter(
                name="address",
                input_types=["str"],
                type="str",
                tooltip="Street address or coordinates (lat,lng) for Street View",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"placeholder_text": "Enter address or lat,lng coordinates..."}
            )
        self.add_node_element(location_group)

        # Image Settings Group
        with ParameterGroup(name="Image Settings") as image_group:
            Parameter(
                name="size",
                input_types=["str"],
                type="str",
                default_value="600x400",
                tooltip="Image size in pixels (width x height). Max 640x640 for free tier.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                traits={Options(choices=["400x300", "600x400", "640x640", "800x600"])}
            )
            Parameter(
                name="heading",
                input_types=["int"],
                type="int",
                default_value=None,
                tooltip="Compass heading of camera (0-360°). Auto if not specified.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"min": 0, "max": 360}
            )
            Parameter(
                name="fov",
                input_types=["int"],
                type="int",
                default_value=90,
                tooltip="Field of view in degrees (10-120°). Lower = more zoom.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"min": 10, "max": 120}
            )
            Parameter(
                name="pitch",
                input_types=["int"],
                type="int",
                default_value=0,
                tooltip="Up/down angle (-90 to 90°). 0 = horizontal.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"min": -90, "max": 90}
            )
        self.add_node_element(image_group)

        # Advanced Settings Group (Collapsed by default)
        with ParameterGroup(name="Advanced Settings") as advanced_group:
            Parameter(
                name="radius",
                input_types=["int"],
                type="int",
                default_value=50,
                tooltip="Search radius in meters for finding Street View imagery.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"min": 1, "max": 1000}
            )
            Parameter(
                name="source",
                input_types=["str"],
                type="str",
                default_value="default",
                tooltip="Imagery source restriction.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                traits={Options(choices=["default", "outdoor"])}
            )
            Parameter(
                name="return_error_code",
                input_types=["bool"],
                type="bool",
                default_value=True,
                tooltip="Return error code instead of generic 'no imagery' image.",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY}
            )
        advanced_group.ui_options = {"hide": True}
        self.add_node_element(advanced_group)

        # Output Parameters
        self.add_parameter(
            Parameter(
                name="street_view_image",
                output_type="ImageUrlArtifact",
                type="ImageUrlArtifact",
                allowed_modes={ParameterMode.OUTPUT},
                tooltip="Street View image as ImageUrlArtifact",
                ui_options={"is_full_width": True, "pulse_on_run": True}
            )
        )
        
        self.add_parameter(
            Parameter(
                name="status",
                output_type="str",
                type="str",
                allowed_modes={ParameterMode.OUTPUT},
                tooltip="Status message about the Street View request",
                ui_options={"multiline": True}
            )
        )

    def validate_node(self) -> list[Exception] | None:
        """Validate Google Maps API key and address format."""
        errors = []
        
        # Check API key (following Kling pattern)
        api_key = self.get_config_value(service=SERVICE, value=API_KEY_ENV_VAR)
        if not api_key:
            errors.append(
                ValueError(f"Google Maps API key not found. Please set the {API_KEY_ENV_VAR} environment variable.")
            )
        
        # Validate address
        address = self.get_parameter_value("address")
        if not address or not address.strip():
            errors.append(ValueError("Address is required."))
        
        # Validate size format
        size = self.get_parameter_value("size")
        if size and not self._validate_size_format(size):
            errors.append(ValueError("Invalid size format. Use 'widthxheight' (e.g., '600x400')."))
        
        return errors if errors else None

    def _validate_size_format(self, size: str) -> bool:
        """Validate size parameter format (widthxheight)."""
        try:
            if 'x' not in size.lower():
                return False
            width, height = size.lower().split('x')
            w, h = int(width), int(height)
            return w > 0 and h > 0 and w <= 640 and h <= 640
        except (ValueError, AttributeError):
            return False

    def _build_request_url(self) -> str:
        """Build the Street View API request URL."""
        api_key = self.get_config_value(service=SERVICE, value=API_KEY_ENV_VAR)
        
        # Required parameters
        params = {
            'location': self.get_parameter_value("address"),
            'size': self.get_parameter_value("size"),
            'key': api_key
        }
        
        # Optional parameters (only add if not default)
        heading = self.get_parameter_value("heading")
        if heading is not None:
            params['heading'] = heading
            
        fov = self.get_parameter_value("fov")
        if fov != 90:
            params['fov'] = fov
            
        pitch = self.get_parameter_value("pitch")
        if pitch != 0:
            params['pitch'] = pitch
            
        radius = self.get_parameter_value("radius")
        if radius != 50:
            params['radius'] = radius
            
        source = self.get_parameter_value("source")
        if source != "default":
            params['source'] = source
            
        if self.get_parameter_value("return_error_code"):
            params['return_error_code'] = 'true'
        
        # URL encode address
        params['location'] = urllib.parse.quote(params['location'])
        
        # Build URL
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{BASE_URL}?{param_string}"

    def _handle_api_response(self, response: requests.Response) -> str:
        """Handle API response and save image using StaticFilesManager."""
        if response.status_code == 404:
            raise ValueError("No Street View imagery available for this location.")
        elif response.status_code == 400:
            raise ValueError("Invalid request parameters.")
        elif response.status_code == 403:
            raise ValueError("API key invalid or quota exceeded.")
        elif response.status_code != 200:
            raise ValueError(f"Street View API error: {response.status_code}")
        
        # Save image using StaticFilesManager
        image_data = response.content
        filename = f"streetview_{int(time.time())}.jpg"
        
        # Use StaticFilesManager to save the image
        image_url = GriptapeNodes.StaticFilesManager().save_static_file(
            image_data,
            filename
        )
        
        return image_url

    def process(self) -> AsyncResult:
        """Generate Street View image."""
        
        def fetch_street_view() -> ImageUrlArtifact:
            try:
                # Debug: Print API key info (following Kling pattern)
                api_key = self.get_config_value(service=SERVICE, value=API_KEY_ENV_VAR)
                logger.info(f"API Key found: {bool(api_key)}")
                if api_key:
                    logger.info(f"API Key (first 10 chars): {api_key[:10]}...")
                    logger.info(f"API Key (last 4 chars): ...{api_key[-4:]}")
                else:
                    logger.error(f"No API key found for service '{SERVICE}' with env var '{API_KEY_ENV_VAR}'")
                
                # Build request URL
                url = self._build_request_url()
                logger.info(f"Requesting Street View image: {url}")
                
                # Make API request
                response = requests.get(url, timeout=30)
                
                # Handle response and save image
                image_url = self._handle_api_response(response)
                
                # Create artifact
                street_view_artifact = ImageUrlArtifact(value=image_url)
                
                # Update outputs
                self.publish_update_to_parameter("street_view_image", street_view_artifact)
                self.publish_update_to_parameter("status", f"Street View image fetched successfully for: {self.get_parameter_value('address')}")
                
                logger.info(f"Street View image saved: {image_url}")
                return street_view_artifact
                
            except Exception as e:
                error_msg = f"Failed to fetch Street View image: {str(e)}"
                logger.error(error_msg)
                self.publish_update_to_parameter("status", error_msg)
                raise RuntimeError(error_msg) from e
        
        yield fetch_street_view 