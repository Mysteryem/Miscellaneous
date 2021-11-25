using UnityEngine;
using UnityEditor;
/*
  Adds Depth Texture toggles to the Context menu for Camera components
  (the same menu where you can Reset/Remove/Copy the component and more)
*/
namespace Mysteryem.Tools {
    class CameraMenuDepthTextureToggle {
        [MenuItem ("CONTEXT/Camera/Depth Texture/Toggle Depth")]
        static void CameraDepthTextureToggleDepth(MenuCommand command) {
              Camera camera = command.context as Camera;
              camera.depthTextureMode ^= DepthTextureMode.Depth;
        }
        
        [MenuItem ("CONTEXT/Camera/Depth Texture/Toggle DepthNormals")]
        static void CameraDepthTextureToggleNormals(MenuCommand command) {
              Camera camera = command.context as Camera;
              camera.depthTextureMode ^= DepthTextureMode.DepthNormals;
        }
        
        // Note that MotionVectors requires Depth and Unity will enable
        // Depth automatically if a Camera has MotionVectors enabled
        [MenuItem ("CONTEXT/Camera/Depth Texture/Toggle MotionVectors")]
        static void CameraDepthTextureToggleMotionVectors(MenuCommand command) {
              Camera camera = command.context as Camera;
              camera.depthTextureMode ^= DepthTextureMode.MotionVectors;
        }
    }
}