set -x -e

VERSION=$1
PROJECT_NAME="shotgun"
BUILD_DIR="$(dirname $0)/build"
DIST_DIR="$(dirname $0)/dist"

BUILD_NAME="$PROJECT_NAME-$VERSION"
BUILD_HOME="$BUILD_DIR/$BUILD_NAME"

mkdir -p "$BUILD_HOME"
mkdir -p "$DIST_DIR"

# Migrate host storage
cp -rv "hoststorage/." "$BUILD_HOME/"

# Pull Dependencies
cd "$BUILD_HOME"
python2 -m pip download -d deps2 -r requirements.txt
cd -

#  Build host storage
cd "$BUILD_HOME"
tar -czvf "../../dist/$BUILD_NAME.tar.gz" *
