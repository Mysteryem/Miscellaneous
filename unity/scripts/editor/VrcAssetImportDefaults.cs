using UnityEditor;
using UnityEngine;
using System;
using System.Reflection;

namespace Mysteryem.Tools.Vrc {
    // Asset preprocessor for VRChat assets, which sets default import settings for newly imported models and textures.
    //
    // Only affects assets that have not been imported into unity before (assets that have no meta file) so it won't affect
    // assets that are imported through a Unity package. It is assumed that assets being imported via a Unity package should be
    // set up for VRChat already.
    public class VrcAssetImportDefaults : AssetPostprocessor {
        
        // PropertyInfo for the legacy blend shape normals property since it isn't public
        private static PropertyInfo _legacyBlendShapeNormalsPropertyInfo;
        // Property getter so the PropertyInfo only needs to be retrieved once instead of retrieved every time
        private static PropertyInfo LegacyBlendShapeNormalsPropertyInfo {
            get {
                if (_legacyBlendShapeNormalsPropertyInfo != null) {
                    return _legacyBlendShapeNormalsPropertyInfo;
                }

                Type modelImporterType = typeof(ModelImporter);
                _legacyBlendShapeNormalsPropertyInfo = modelImporterType.GetProperty(
                    "legacyComputeAllNormalsFromSmoothingGroupsWhenMeshHasBlendShapes",
                    BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public
                );

                return _legacyBlendShapeNormalsPropertyInfo;
            }
        }
        
        // Enables Read/Write and Legacy Blend Shape Normals on models
        // Logs a warning if the model has vertices assigned to more than 4 bones
        void OnPreprocessModel() {
            // Get the ModelImporter instance
            ModelImporter modelImporter = (ModelImporter)assetImporter;
            
            // If it's a new import into a project, it won't have an existing meta file
            if (modelImporter.importSettingsMissing) {
                // Log that we're doing something
                Debug.Log("Detected initial import of model " + modelImporter.assetPath + ". Enabling Read/Write and Enabling Legacy Blend Shape Normals");
                
                // Enable read/write
                // This must be on, otherwise the VRCSDK can't check how many polygons there are and assumes the maximum value,
                // immediately putting the avatar into very poor performance ranking
                modelImporter.isReadable = true;
                
                // Enable legacy blend shape normals
                // This must be on, otherwise the VRCSDK will reject uploading the avatar
                // This setting is non-public so must be set with reflection
                if (LegacyBlendShapeNormalsPropertyInfo != null) {
                    LegacyBlendShapeNormalsPropertyInfo.SetValue(modelImporter, true);
                }
                // The legacy blend shape normals option appears to be the same as calculating normals from smoothing groups
                // when there are blendshapes
                // If we know the meshes have blendshapes, it should have the same effect as doing:
                //modelImporter.importBlendShapeNormals = ModelImporterNormals.Calculate;
                //modelImporter.normalSmoothingSource = ModelImporterNormalSmoothingSource.FromSmoothingGroups;
                // This might result in different behaviour when some of the meshes don't have blendshapes however
            }
            
            // VRChat only allows up to 4 bones per vertex, any vertices with more than 4 will have their lowest bone weights
            // bones discarded until there are only 4
            if (modelImporter.maxBonesPerVertex > 5) {
                Debug.LogWarning(modelImporter.assetPath + " has vertices weight painted to more than 4 bones. The lowest bone weights will be discarded by VRChat until there are only 4, regardless of the Skin Weights setting in the Rig tab of the model import settings.");
            }
        }
        
        // Enables streaming mipmaps on textures
        void OnPreprocessTexture() {
            // Get the TextureImporter isntance
            TextureImporter textureImporter = (TextureImporter)assetImporter;
            
            // If it's a new import into a project, it won't have an existing meta file
            if (textureImporter.importSettingsMissing) {
                // Streaming mipmaps must be enabled to upload to VRC
                textureImporter.streamingMipmaps = true;
            }
        }
    }
}