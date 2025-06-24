# Google Maps Nodes

This library provides Griptape Nodes for integrating with Google Maps services. You can use these nodes to fetch Street View images from addresses or coordinates.

**IMPORTANT:** To use these nodes, you will need a Google Maps API key. Please visit the [Google Cloud Console](https://console.cloud.google.com) to:
1. Create a project with billing enabled
2. Enable the Street View Static API
3. Generate an API key

To configure your API key within the Griptape Nodes IDE:
1. Set the environment variable: `export GOOGLE_MAPS_API_KEY="your_api_key_here"`
2. Restart your Griptape Nodes engine

Below is a description of the node and its parameters.

### Google Street View (`GoogleStreetView`)

Fetches Street View images from Google's Street View Static API using an address or coordinates.

| Parameter | Type | Description | Default Value |
|-----------|------|-------------|---------------|
| `address` | `str` | Street address or lat/lng coordinates (e.g., "1600 Amphitheatre Parkway, Mountain View, CA" or "37.4218,-122.0841") | |
| `size` | `str` | Image dimensions in pixels (widthxheight). Max 640x640 for free tier. Choices: `400x300`, `600x400`, `640x640`, `800x600` | `600x400` |
| `heading` | `int` | Camera compass direction in degrees (0-360°). Auto if not specified. | `None` |
| `fov` | `int` | Field of view/zoom level in degrees (10-120°). Lower = more zoom. | `90` |
| `pitch` | `int` | Up/down camera angle (-90 to 90°). 0 = horizontal. | `0` |
| `radius` | `int` | Search radius in meters for finding Street View imagery (1-1000). | `50` |
| `source` | `str` | Imagery source restriction. Choices: `default`, `outdoor` | `default` |
| `return_error_code` | `bool` | Return error code instead of generic 'no imagery' image. | `True` |
| `street_view_image` | `ImageUrlArtifact` | **Output:** Street View image as ImageUrlArtifact | `None` |
| `status` | `str` | **Output:** Status message about the Street View request | `None` |

*Note: `Location`, `Image Settings`, and `Advanced Settings` parameters are grouped and may be collapsed by default in the UI.*

## Add your library to your installed Engine! 

If you haven't already installed your Griptape Nodes engine, follow the installation steps [HERE](https://github.com/griptape-ai/griptape-nodes).
After you've completed those and you have your engine up and running: 

1. Copy the path to your `griptape_nodes_library.json` file within the `google-maps` directory. Right click on the file, and `Copy Path` (Not `Copy Relative Path`).
2. Start up the engine! 
3. Navigate to settings.
4. Open your settings and go to the App Events tab. Add an item in **Libraries to Register**.
5. Paste your copied `griptape_nodes_library.json` path from earlier into the new item.
6. Exit out of Settings. It will save automatically! 
7. Open up the **Libraries** dropdown on the left sidebar.
8. Your newly registered library should appear! Drag and drop nodes to use them!

## API Key Security & Best Practices

- **Free Tier**: 28,000 requests per month
- **Paid Usage**: Charged per request after free tier
- **Security**: Restrict your API key to Street View Static API only
- **Monitoring**: Track usage in [Google Cloud Console](https://console.cloud.google.com)
