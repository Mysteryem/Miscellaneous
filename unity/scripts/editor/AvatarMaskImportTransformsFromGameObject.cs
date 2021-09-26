/*
TODO: This script is in dire need of some cleanup and reorganising.
This works well enough for now, you can find the tool in the "Tools" menu under "Mysteryem" once added to your project.
Make sure that you put this within a folder called Editor so that compilation errors won't occur when trying to upload a VRChat avatar or run your Unity application.
*/
using UnityEditor;
using UnityEngine;
using System;

namespace Mysteryem.Tools {
    // Editor window for importing transforms to an AvatarMask from a GameObject instead of from a skeleton
    public class AvatarMaskImportTransformsFromGameObject : EditorWindow {
        private AvatarMask mask;
        private GameObject gameObject;
        private GameObject rootGameObject;
        
        [MenuItem("Tools/Mysteryem/Import Avatar Mask Transforms From GameObject")]
        static void Init() {
            var window = GetWindow(typeof(AvatarMaskImportTransformsFromGameObject), true, "Avatar Mask Transform Import Tool");
        }
        
        public void OnGUI() {
            GUILayout.Label("Import Transforms into an AvatarMask using a GameObject for reference instead of an Avatar's skeleton (replaces existing imported transforms).\nFor a VRChat avatar, this lets you include GameObjects added in Unity in your AvatarMasks, allowing Transforms of added GameObjects to be masked and animated in the Gesture layer.", EditorStyles.wordWrappedLabel);
            
            mask = EditorGUILayout.ObjectField("Mask", mask, typeof(AvatarMask), false) as AvatarMask;
            gameObject = EditorGUILayout.ObjectField("GameObject", gameObject, typeof(GameObject), true) as GameObject;
            
            // If is part of prefab asset/instance it cannot be reordered, but can get root
            // I think this is corrent and not PrefabUtility.GetNearestPrefabInstanceRoot(gameObject), since Outermost will correctly get the root of an added prefab, which can be reparented, whereas Nearest could get a prefab within a prefab which can't be reparented
            GameObject outermostPrefabInstanceRoot = gameObject == null ? null : PrefabUtility.GetOutermostPrefabInstanceRoot(gameObject);
            bool isInPrefab = outermostPrefabInstanceRoot != null;
            if (isInPrefab) {
                rootGameObject = outermostPrefabInstanceRoot;
            } else {
                rootGameObject = gameObject;
            }
            
            bool needsTemporaryRooting = rootGameObject == null ? false : rootGameObject.transform.parent != null;
            bool isInPrefabAsset = false;
            
            // I don't see a way to get a prefab root from a prefab asset, only from prefab instances, so we'll do a more manual check
            if (rootGameObject != null && PrefabUtility.IsPartOfPrefabAsset(rootGameObject)) {
                needsTemporaryRooting = false;
                isInPrefabAsset = true;
                isInPrefab = true;
            }
            
            if (isInPrefabAsset) {
                //if (gameObject.transform.parent != null) {
                //    rootGameObject = gameObject.transform.parent.gameObject;
                //}
                while(rootGameObject.transform.parent != null) {
                    rootGameObject = gameObject.transform.parent.gameObject;
                }
            }
            
            bool isPrefabRoot = gameObject == rootGameObject;
            bool isChildInPrefab = isInPrefab && !isPrefabRoot;
            
            if (isChildInPrefab) {
                using (new EditorGUI.DisabledScope(true)) {
                    EditorGUILayout.ObjectField("Root GameObject", rootGameObject, typeof(GameObject), true);
                }
            }
            
            if (isChildInPrefab) {
                GUILayout.Label("Importing directly from a GameObject within a prefab is not supported at this time",
                    EditorStyles.wordWrappedMiniLabel);
            }
            
            using (new EditorGUI.DisabledScope(mask == null || gameObject == null || isChildInPrefab)) {
                DoImportButton("Import transforms from GameObject", gameObject, needsTemporaryRooting);
            }
            
            if (isChildInPrefab) {
                using (new EditorGUI.DisabledScope(mask == null || rootGameObject == null)) {
                    DoImportButton("Import transforms from Root GameObject", rootGameObject, needsTemporaryRooting);
                }
            }
        }
        
        void DoImportButton(String buttonMessage, GameObject chosenObject, bool needsTemporaryRooting) {
          if (GUILayout.Button(buttonMessage)) {
                  if (chosenObject != null && mask != null) {
                      mask.transformCount = 0;
                      
                      Transform rootTransform = chosenObject.transform;
                      
                      Transform parent = null;
                      int siblingIndex = rootTransform.GetSiblingIndex();
                      if (needsTemporaryRooting) {
                          parent = rootTransform.parent;
                          rootTransform.parent = null;
                      }
                      mask.AddTransformPath(rootTransform);
                      Debug.Log("Imported transforms recursively from " + rootTransform);
                      if (needsTemporaryRooting) {
                          rootTransform.parent = parent;
                          rootTransform.SetSiblingIndex(siblingIndex);
                      }
                  }
              }
        }
    }
}
