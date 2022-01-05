using UnityEditor;
using UnityEngine;
using UniGLTF; //for the extension to Transform: UniGLTF.UnityExtensions.RelativePathFrom(Transform node, Transform root)
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using VRM;

namespace Mysteryem.Tools {
  
    /*  Editor window for adding and/or fixing arkit blendshapes for VRM
    
        Currently only allows for creating and adding ARKit BlendShapeClips that don't currently exist.
        
        Being able to fix existing BlendShapeClips is planned since reordering blendshapes in a mesh will cause BlendShapeClips to
        activate the wrong blendshapes since BlendShapeClips save the blendshape index rather than the blendshape name
    
        Assumes each ARKit BlendShapeClip activates a single blendshape 100% with a name that is the same as the name of the BlendShapeClip,
        with an optional prefix or suffix and optionally ignoring case
    */
    public class VRMBlendShapeTools : EditorWindow {
        private static string[] ARKIT_NAMES = {"BrowDownLeft", "BrowDownRight", "BrowInnerUp", "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff", "CheekSquintLeft", "CheekSquintRight", "EyeBlinkLeft", "EyeBlinkRight", "EyeLookDownLeft", "EyeLookDownRight", "EyeLookInLeft", "EyeLookInRight", "EyeLookOutLeft", "EyeLookOutRight", "EyeLookUpLeft", "EyeLookUpRight", "EyeSquintLeft", "EyeSquintRight", "EyeWideLeft", "EyeWideRight", "JawForward", "JawLeft", "JawOpen", "JawRight", "MouthClose", "MouthDimpleLeft", "MouthDimpleRight", "MouthFrownLeft", "MouthFrownRight", "MouthFunnel", "MouthLeft", "MouthLowerDownLeft", "MouthLowerDownRight", "MouthPressLeft", "MouthPressRight", "MouthPucker", "MouthRight", "MouthRollLower", "MouthRollUpper", "MouthShrugLower", "MouthShrugUpper", "MouthSmileLeft", "MouthSmileRight", "MouthStretchLeft", "MouthStretchRight", "MouthUpperUpLeft", "MouthUpperUpRight", "NoseSneerLeft", "NoseSneerRight", "TongueOut"};
        // Precompute lowercase names
        private static string[] ARKIT_NAMES_LOWER = ARKIT_NAMES.Select(s => s.ToLower()).ToArray();
        // Precompute BlendShapeKeys
        private static BlendShapeKey[] ARKIT_KEYS = ARKIT_NAMES.Select(s => BlendShapeKey.CreateUnknown(s)).ToArray();
        
        private BlendShapeAvatar blendShapeAvatar;
        private GameObject prefab;
        private int meshIndex = 0;
        private string blendShapePrefix = "";
        private string blendShapeSuffix = "";
        private string clipDirectory;
        private bool blendShapeNameCaseSensitive;
        private SkinnedMeshRenderer[] meshRendererOptions = {};
        private string[] meshRendererRelativePaths = {};
        
        // Maybe put this in Tools/Mysteryem/ instead of in the VRM menu
        [MenuItem(VRMVersion.MENU + "/Mysteryem/ARKit BlendShape Helper")]
        static void Init() {
            var window = GetWindow(typeof(VRMBlendShapeTools), true, "ARKit BlendShape Helper");
        }
        
        private string GetClipPath(string clipName) {
            if (this.clipDirectory == null) {
                return null;
            }
            return this.clipDirectory + "/" + clipName + ".asset";
        }
        
        public void OnGUI() {
            // Draw and input for a prefab
            var pickedPrefab = EditorGUILayout.ObjectField("Prefab", this.prefab, typeof(GameObject), false) as GameObject;
            bool prefabChanged = pickedPrefab != this.prefab;
            this.prefab = pickedPrefab;
            
            // Draw an input for a BlendShapeAvatar
            this.blendShapeAvatar = EditorGUILayout.ObjectField("BlendShapeAvatar", this.blendShapeAvatar, typeof(BlendShapeAvatar), false) as BlendShapeAvatar;
            
            if (this.blendShapeAvatar != null) {
                // Set directory for saving new BlendShapeClips from the BlendShapeAvatar
                this.clipDirectory = Path.GetDirectoryName(AssetDatabase.GetAssetPath(this.blendShapeAvatar));
                if (!string.IsNullOrEmpty(this.clipDirectory)) {
                    GUILayout.Label("Clip directory is: " + this.clipDirectory, EditorStyles.wordWrappedLabel);
                }
            }
            
            float labelWidth = EditorGUIUtility.labelWidth;
            EditorGUIUtility.labelWidth = labelWidth + 50.0f;
            
            // Draw inputs for blendshape prefix and suffix
            this.blendShapePrefix = EditorGUILayout.TextField("Mesh BlendShape prefix", this.blendShapePrefix);
            this.blendShapeSuffix = EditorGUILayout.TextField("Mesh BlendShape suffix", this.blendShapeSuffix);
            
            // Draw input for blendshape case sensitivity
            this.blendShapeNameCaseSensitive = EditorGUILayout.Toggle("Mesh BlendShape case sensitive", this.blendShapeNameCaseSensitive);
            
            EditorGUIUtility.labelWidth = labelWidth;
            
            if (!this.blendShapeNameCaseSensitive) {
                this.blendShapePrefix = this.blendShapePrefix.ToLower();
                this.blendShapeSuffix = this.blendShapeSuffix.ToLower();
            }
            
            if (prefabChanged) {
                if (this.prefab != null) {
                    // This can be quite slow, so we're only doing it when the prefab changes
                    // Get all SkinnedMeshRenderers in the prefab - This can be quite slow if a the prefab hasn't been used in a while
                    SkinnedMeshRenderer[] skinnedMeshRenderers = this.prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                    //GUILayout.Label("Num SkinnedMeshRenderers found = " + skinnedMeshRenderers.Length, EditorStyles.wordWrappedLabel);
                    // Filter out any without a mesh or without any blend shapes
                    var optionsWhere = skinnedMeshRenderers
                        .Where(renderer => renderer.sharedMesh != null && renderer.sharedMesh.blendShapeCount > 0);
                    // Convert to an Array
                    this.meshRendererOptions = optionsWhere.ToArray();
                    // Take the same filtered enumuration of the array and map each element to its relative path from the prefab, then convert to an array
                    this.meshRendererRelativePaths = optionsWhere
                        .Select(renderer => renderer.transform.RelativePathFrom(this.prefab.transform))
                        .ToArray();
                    
                    // TODO: Try to guess which mesh to select. Options:
                    // Mesh name: contains 'face' or 'head' case insensitive
                    // Number of blendshapes: ARKit uses 52 blendshapes, so the face mesh is expected to have at least 52
                    // Names of blendshapes: We could search through the blendshapes, looking for ones (or one) with a similar name to ARKit blendshape names
                    //                       This is an expensive operation though since it requires going through all the blendshapes in each mesh
                    this.meshIndex = GetIndexForMeshWithMostBlendShapes(this.meshRendererOptions);
                    
                } else {
                    this.meshRendererOptions = new SkinnedMeshRenderer[0];
                    this.meshRendererRelativePaths = new string[0];
                    this.meshIndex = 0;
                }
            }
            
            // TODO: Figure out how to disable the delimiting by '/'
            // Draw a drop down list of the different choices for face mesh
            using (new EditorGUI.DisabledScope(this.meshRendererRelativePaths.Length == 0)) {
                this.meshIndex = EditorGUILayout.Popup("Face Mesh", this.meshIndex, this.meshRendererRelativePaths);
            }
            
                
                
            bool foundMesh = this.meshIndex < this.meshRendererOptions.Length;
            
            // Set the face SkinnedMeshRenderer if one is chosen and its relative path from the prefab
            SkinnedMeshRenderer faceRenderer;
            string meshRelativePath;
            if (foundMesh) {
                faceRenderer = this.meshRendererOptions[this.meshIndex];
                meshRelativePath = this.meshRendererRelativePaths[this.meshIndex];
            } else {
                faceRenderer = null;
                meshRelativePath = null;
            }
            
            bool disableAddButton = faceRenderer == null || this.blendShapeAvatar == null;
            
            // Disable button if there is no face SkinnedMeshRenderer
            using (new EditorGUI.DisabledScope(disableAddButton)) {
                // Draw button for 
                if (GUILayout.Button("Add ARKit BlendShapeClips")) {
                    // We've already filtered the SkinnedMeshRenders for those with non-null sharedMesh so we assume this is non-null
                    Mesh mesh = faceRenderer.sharedMesh;
                    AddARKitBlendShapeClips(mesh, meshRelativePath);
                }
            }
        }
        
        private void AddARKitBlendShapeClips(Mesh mesh, string meshRelativePath) {
            // Create dictionary to look up shape key indices, lower-casing shape key names if case sensitive is not ticked
            Dictionary<string, int> lowerNameToIndex = new Dictionary<string, int>();
            for (int i = 0; i < mesh.blendShapeCount; i++) {
                
                var blendShapeName = mesh.GetBlendShapeName(i);
                if (!this.blendShapeNameCaseSensitive) {
                    blendShapeName = blendShapeName.ToLower();
                }
                lowerNameToIndex[blendShapeName] = i;
            }
            

            List<string> clipFileAlreadyExistsList = new List<string>();
            List<string> clipBlendShapeNotFoundList = new List<string>();
            
            for (int i = 0; i < ARKIT_NAMES.Length; i++) {
                var clipKey = ARKIT_KEYS[i];
                var clipName = ARKIT_NAMES[i];
                var clipFromAvatar = this.blendShapeAvatar.GetClip(clipKey);
                
                // Only proceed if the BlendShapeAvatar doesn't already have a BlendShapeClip with this key assigned
                if (clipFromAvatar == null) {
                    string clipPath = this.GetClipPath(ARKIT_NAMES[i]);
                    var clipFromFile = UnityEditor.AssetDatabase.LoadAssetAtPath<BlendShapeClip>(clipPath);
                    
                    // Only proceed if the file for the BlendShapeClip doesn't exist
                    if (clipFromFile == null) {
                        int blendShapeIndex;
                        // Combine the prefix, suffix and ARKit name to get the expected name of the blendshape on the mesh
                        string blendShapeName = this.blendShapePrefix
                                                + (this.blendShapeNameCaseSensitive ? ARKIT_NAMES[i] : ARKIT_NAMES_LOWER[i])
                                                + this.blendShapeSuffix;
                        // Get the index of the blendshape on the face mesh if it exists
                        if (lowerNameToIndex.TryGetValue(blendShapeName, out blendShapeIndex)) {
                            // Create the Binding which will specify the blendshape to activate
                            var binding = new BlendShapeBinding
                            {
                                RelativePath = meshRelativePath,
                                Index = blendShapeIndex,
                                Weight = 100f,
                            };
                            
                            // Create a new BlendShapeClip
                            // This is probably the slowest part since each call creates and then imports an asset
                            var clip = BlendShapeAvatar.CreateBlendShapeClip(clipPath);
                            
                            // Set the list of Bindings (just our one binding)
                            clip.Values = new BlendShapeBinding[]{binding};
                            // The default value should be false so no need to set this
                            //clip.IsBinary = false;
                            
                            // Set the newly created clip in the BlendShapeAvatar
                            blendShapeAvatar.SetClip(clipKey, clip);
                            
                            // BlendShapeAvatar.CreateBlendShapeClip(...) has some commented out lines that do this along with AssetDatabase.SaveAssets()
                            // Without these, the changes to not necessarily get saved
                            EditorUtility.SetDirty(this.blendShapeAvatar);
                        } else {
                            clipBlendShapeNotFoundList.Add(blendShapeName);
                        }
                    } else {
                        clipFileAlreadyExistsList.Add(clipPath);
                    }
                }
            }
            AssetDatabase.SaveAssets();
            
            if (clipFileAlreadyExistsList.Count != 0) {
                Debug.Log("Failed to create some BlendShapeClips as the files already exist, but are not part of the BlendShapeAvatar:\n" + String.Join("\n", clipFileAlreadyExistsList));
            }
            
            if (clipBlendShapeNotFoundList.Count != 0) {
                Debug.Log("Failed to create some BlendShapeClips as the blendshapes could not be found on the face mesh" + (this.blendShapeNameCaseSensitive ? "" : " (case insensitive)") + ":\n" + String.Join("\n", clipBlendShapeNotFoundList));
            }
        }
        
        // All renderers are assumed to have a non-null sharedMesh where sharedMesh.blendShapeCount > 0
        private static int GetIndexForMeshWithMostBlendShapes(SkinnedMeshRenderer[] renderers) {
            int mostBlendShapes = 0;
            int indexToReturn = 0;
            
            for (int i = 0; i < renderers.Length; i++) {
                var renderer = renderers[i];
                int numBlendShapes = renderer.sharedMesh.blendShapeCount;
                if (numBlendShapes > mostBlendShapes) {
                    mostBlendShapes = numBlendShapes;
                    indexToReturn = i;
                }
            }
            
            return indexToReturn;
        }
    }
}