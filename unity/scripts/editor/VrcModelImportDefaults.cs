using UnityEditor;
using UnityEngine;
using System;
using System.Reflection;

namespace Mysteryem.Tools.Vrc {
    // Model preprocessor for VRChat which enables Read/Write and Legacy Blend Shape Normals by default on newly imported models
    // Only affects models that have not been imported into unity before (models that have no meta file) so it won't affect
    // models that are imported through a Unity package. It is assumed that models being imported via a Unity package should be
    // set up for VRChat already.
    public class VrcModelImportDefaults : AssetPostprocessor {
        
        // PropertyInfo for the legacy blend shape normals property
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
        
        void OnPreprocessModel() {
            // Get the ModelImporter instance
            ModelImporter modelImporter = assetImporter as ModelImporter;
            
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
                // The legacy  blend shape normals option is the same as calculating from smoothing groups,
                // but the VRCSDK checks for only the legacy tickbox, so we have to do the same PropertyInfo mess
                // to set the checkbox since it's not public
                // The legacy option is the same as setting the blendshape normals to calculate from smoothing groups
                // but the VRCSDK unfortunately doesn't check these. If it did, we could instead do:
                //modelImporter.importBlendShapeNormals = ModelImporterNormals.Calculate;
                //modelImporter.normalSmoothingSource = ModelImporterNormalSmoothingSource.FromSmoothingGroups;
            }
        }
    }
}