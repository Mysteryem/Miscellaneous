using UnityEditor;
using UnityEngine;
using System;
using System.Collections.Generic;

namespace Mysteryem.Tools {
    public class MeshTangentUtils {
        // Default overload method to two uv channels (x and y) since uvs are almost always x and y only unless you're doing
        // fancy stuff in Unity
        public static void RecalculateTangents(Mesh mesh, int uvChannel) {
            RecalculateTangents(mesh, uvChannel, 2);
        }

        // I'm not used to C#'s stronger typed generics compared to Java, this seems to work to reduce the amount of duplicate
        // code needed to handle each different number of uvChannels. I assume it's slower, but since this is only going to be run at most once per mesh in the import, the speed difference should be negligible.
        public static void RecalculateTangents(Mesh mesh, int uvChannel, int uvComponents) {
            Func<object> constructList;
            switch(uvComponents) {
                case 2:
                    constructList = () => new List<Vector2>();
                    break;
                case 3:
                    constructList = () => new List<Vector3>();
                    break;
                case 4:
                    constructList = () => new List<Vector4>();
                    break;
                default:
                    Debug.LogWarning("Invalid number of uv components '" + uvComponents + "'. Must be 2-4 inclusive.");
                    return;
            }
            // We do get direct access to mesh.uv, mesh.uv2, mesh.uv3 etc., but these all only let us use Vector2
            // GetUVs and SetUVs let us use up to Vector4, each of the methods takes a List<Vector#> arguments instead
            // of returning a new list and there are separate overloads for Vector2, Vector3 and Vector4.
            // As an implementation note, the Unity scripting docs say that to update uvs, the entire list needs to be copied,
            // updated and then the uvs entirely replaced with that copied and updated list.
            var uv0 = constructList();
            var uvChoice = constructList();
            // Store the uvs of the first uv map into the first list
            mesh.GetUVs(0, (dynamic)uv0);
            // Store the uvs of the uv map to generate tangents from into the other list
            mesh.GetUVs(uvChannel, (dynamic)uvChoice);
            // Set the first uv map to the uvs the tangents will be generated from
            mesh.SetUVs(0, (dynamic)uvChoice);
            // Recalculate the tangents (uses the first uv map and I assume Mikktspace, but there is a lack of documentation here)
            mesh.RecalculateTangents();
            // Restore the first uv map back to what it was originally
            mesh.SetUVs(0, (dynamic)uv0);
        }
    }
    
    // Asset Postprocessor that lets you use a custom property in an FBX to recalculate the vertex tangents of a mesh based
    // on a specific uv map of the mesh. From looking at Blender's FBX exporter, I think it saves separate tangents for each
    // uv map, but Unity only lets you import the tangents from the first uv map. Unity also lets you calculate tangents
    // on import, but again, it has no options to use a different uv map to the first one.
    // 
    // As Unity doesn't let you specify a uv map when recalculating tangents via script, this script temporarily copies the
    // wanted uv map into the first uv map, recalculates the tangents and then puts the first uv map back
    //
    // Note that Blender lets you specify Custom Properties in a number of areas, for this script (and seeming all scripts
    // that work similarly), the Custom Properties have to be added to the Object Properties, not the Object Data Properties
    // or anywhere else
    public class MeshTangentPostprocessor : AssetPostprocessor {
        private static string TANGENT_MAP_PROP_NAME = "MYSTERYEM_TANGENT_UV_MAP";
        
        // Runs after import, but before the imported object is saved into a prefab
        void OnPostprocessGameObjectWithUserProperties(GameObject go, string[] propNames, object[] values) {
            //var modelImporter = (ModelImporter)assetImporter;
            // Iterate through the array of custom properties looking for our special key
            for (int i = 0; i < propNames.Length; i++) {
                if (propNames[i] == TANGENT_MAP_PROP_NAME) {
                    object value = (object)values[i];
                    // Currently requires the value to be an int, but it might be wise to also allow a string that can be
                    // parsed as an int
                    if (value is int) {
                        int uvMapIndex = (int)value;
                        // Unity supports up to 8 uv maps:
                        // uv, uv2, uv3, uv4, uv5, uv6, uv7, uv8
                        //  0,   1,   2,   3,   4,   5,   6,   7
                        if (uvMapIndex < 8 && uvMapIndex >= 0) {
                            // The GameObject we get has the Mesh in a MeshFilter
                            var mf = go.GetComponent<MeshFilter>();
                            if (mf != null) {
                                // note that mf.mesh is a copy so we can't use that
                                // whereas modifying mf.sharedMesh isn't and changes to it will affect the prefab
                                var mesh = mf.sharedMesh;
                                MeshTangentUtils.RecalculateTangents(mesh, uvMapIndex);
                                Debug.Log("Recalculated tangents for " + go + ", using uv" + uvMapIndex);
                                break;
                            } else {
                                Debug.Log("Failed to find Mesh for " + go);
                            }
                        } else {
                            Debug.Log("Invalid uvmap index " + value + " for " + go);
                        }
                    } else {
                        Debug.Log("Invalid uvmap index " + value + " for " + go);
                    }
                }
            }
        }
    }
    
    // Standalone Editor Window for swapping mesh tangents
    public class MeshTangentRecalculator : EditorWindow {
        private static string[] uvChannelNames = new string[8];
        private static int[] uvChannelValues = new int[8];
        private static string[] uvDimensionNames = new string[]{"xy", "xyz", "xyzw"};
        private static int[] uvDimensionValues = new int[]{2, 3, 4};
        
        // Static initialiser to populate uvChannelNames and uvChannelValues
        static MeshTangentRecalculator() {
            for (int i = 0; i < MeshTangentRecalculator.uvChannelNames.Length; i++) {
                  MeshTangentRecalculator.uvChannelNames[i] = "uv" + i;
                  MeshTangentRecalculator.uvChannelValues[i] = i;
            }
        }
      
        private GameObject prefab;
        private int uvChannel = 1;
        private Mesh mesh;
        private int uvDimensions = 2;

        [MenuItem("Tools/Mysteryem/Mesh Tangent Recalculator")]
        static void Init() {
            GetWindow(typeof(MeshTangentRecalculator), true, "Tangents Recalculator");
        }

        public void OnGUI() {
            this.mesh = EditorGUILayout.ObjectField("Mesh", mesh, typeof(Mesh), false) as Mesh;
            this.uvChannel = EditorGUILayout.IntPopup("UV Map", this.uvChannel, MeshTangentRecalculator.uvChannelNames, MeshTangentRecalculator.uvChannelValues);
            this.uvDimensions = EditorGUILayout.IntPopup("UV Dimensions", this.uvDimensions, MeshTangentRecalculator.uvDimensionNames, MeshTangentRecalculator.uvDimensionValues);
            bool isInvalid = this.mesh == null || this.uvChannel < uvChannelValues[0] || this.uvChannel > uvChannelValues[uvChannelValues.Length-1] || this.uvDimensions < uvDimensionValues[0] || this.uvDimensions > uvDimensionValues[uvDimensionValues.Length-1];
            using (new EditorGUI.DisabledScope(isInvalid)) {
                if (GUILayout.Button("Recalculate Tangents For " + MeshTangentRecalculator.uvChannelNames[this.uvChannel])) {
                    MeshTangentUtils.RecalculateTangents(this.mesh, this.uvChannel, this.uvDimensions);
                    Debug.Log("Recalculated tangents for " + this.mesh.name + ", using uv" + this.uvChannel);
                }
            }
        }
    }
}