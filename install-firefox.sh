# Use the Unbranded build that corresponds to a specific Firefox version 
# To upgrade:
#    1. Go to: https://hg.mozilla.org/releases/mozilla-release/tags.
#    2. Find the commit hash for the Firefox release version you'd like to upgrade to.
#    3. Update the `TAG` variable below to that hash.

TAG='25e0edbb0a613c3bf794c93ba3aa0985d29d5ef4'

case "$(uname -s)" in
   Darwin)
     echo 'Installing for Mac OSX'
     OS='macosx'
     TARGET_SUFFIX='.dmg'
     ;;
   Linux)
     echo 'Installing for Linux'
     OS='linux'
     TARGET_SUFFIX='.tar.bz2'
     ;;
   *)
     echo 'Your OS is not supported. Aborting'
     exit 1
     ;;
esac

UNBRANDED_RELEASE_BUILD="https://firefox-ci-tc.services.mozilla.com/api/index/v1/task/gecko.v2.mozilla-release.revision.${TAG}.firefox.${OS}64-add-on-devel/artifacts/public/build/target${TARGET_SUFFIX}"
wget "$UNBRANDED_RELEASE_BUILD"

case "$(uname -s)" in
   Darwin)
     rm -rf Nightly.app || true
     hdiutil attach -nobrowse -mountpoint /Volumes/firefox-tmp target.dmg
     cp -r /Volumes/firefox-tmp/Nightly.app .
     hdiutil detach /Volumes/firefox-tmp
     rm target.dmg
     ;;
   Linux)
     tar jxf target.tar.bz2
     rm -rf firefox-bin
     mv firefox firefox-bin
     rm target.tar.bz2
     ;;
esac

echo 'Firefox succesfully installed'